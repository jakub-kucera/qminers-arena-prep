//! python/bots/rivals/trapper.py in Rust.

use super::*;
use crate::arena::engine::{Bot, TickView};
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder, Price};
use crate::support::json::Value;

pub struct Trapper {
    limits: Limits,
    bait_size: i64,
    period: i64,
    cooldown_ticks: i64,
    tick: i64,
    bait: Vec<Option<(bool, Price)>>, // per product: last tick's bait (bid side?, price)
    cooldown: Vec<i64>,
}

impl Trapper {
    pub fn from_globals(globals: &Value) -> Result<Trapper, String> {
        Ok(Trapper {
            limits: Limits::read(globals)?,
            bait_size: int(globals, "BAIT")?,
            period: int(globals, "PERIOD")?,
            cooldown_ticks: int(globals, "COOLDOWN")?,
            tick: 0,
            bait: Vec::new(),
            cooldown: Vec::new(),
        })
    }
}

impl Bot for Trapper {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
        self.tick = 0;
        self.bait = vec![None; day.products.len()];
        self.cooldown = vec![0; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let limit = self.limits.by_product[product];
            cancels(product, open_orders, out);
            let book = tick.books[product].as_ref().unwrap();
            if book.bids.is_empty() || book.asks.is_empty() {
                continue;
            }
            let fair = outer_fair(book);
            let position = positions[product];
            let (mut buy_room, mut sell_room) = (limit - position, limit + position);
            let mut bid_side = self.tick.div_euclid(self.period).rem_euclid(2) == 0;
            if position > limit.div_euclid(2) {
                bid_side = false;
            } else if position < (-limit).div_euclid(2) {
                bid_side = true;
            }

            // Spring: someone stepped in front of last tick's bait.
            let mut sprung = false;
            if let Some((bid, price)) = self.bait[product] {
                if bid && book.bids[0].0 == price + 1 && sell_room > 0 {
                    let q = book.bids[0].1.min(sell_room);
                    out.push(ioc(product, book.bids[0].0, -q));
                    sell_room -= q;
                    sprung = true;
                } else if !bid && book.asks[0].0 == price - 1 && buy_room > 0 {
                    let q = book.asks[0].1.min(buy_room);
                    out.push(ioc(product, book.asks[0].0, q));
                    buy_room -= q;
                    sprung = true;
                }
            }
            if sprung {
                self.cooldown[product] = self.cooldown_ticks;
            }

            take_through(product, book, fair, position, &mut buy_room, &mut sell_room, out);

            let mut bait = None;
            if self.cooldown[product] > 0 {
                self.cooldown[product] -= 1;
            } else if bid_side && buy_room > 0 {
                let price = (book.bids[0].0 + 1).min((fair - 0.5).floor() as i64);
                if price < book.asks[0].0 {
                    out.push(rest(product, price, self.bait_size.min(buy_room)));
                    bait = Some((true, price));
                }
            } else if !bid_side && sell_room > 0 {
                let price = (book.asks[0].0 - 1).max((fair + 0.5).ceil() as i64);
                if price > book.bids[0].0 {
                    out.push(rest(product, price, -self.bait_size.min(sell_room)));
                    bait = Some((false, price));
                }
            }
            self.bait[product] = bait;
        }
        self.tick += 1;
    }
}
