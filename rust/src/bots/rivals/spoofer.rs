//! python/bots/rivals/spoofer.py in Rust.

use super::*;
use crate::arena::engine::{Bot, TickView};
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};
use crate::support::json::Value;

pub struct Spoofer {
    limits: Limits,
    spoof: i64,
    offset: i64,
    period: i64,
    tick: i64,
}

impl Spoofer {
    pub fn from_globals(globals: &Value) -> Result<Spoofer, String> {
        Ok(Spoofer { limits: Limits::read(globals)?, spoof: int(globals, "SPOOF")?, offset: int(globals, "OFFSET")?, period: int(globals, "PERIOD")?, tick: 0 })
    }
}

impl Bot for Spoofer {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
        self.tick = 0;
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
            let bid_side = self.tick.div_euclid(self.period).rem_euclid(2) == 0;
            take_through(product, book, fair, position, &mut buy_room, &mut sell_room, out);
            if bid_side && buy_room > 0 {
                out.push(rest(product, book.bids[0].0 - self.offset, self.spoof.min(buy_room)));
            } else if !bid_side && sell_room > 0 {
                out.push(rest(product, book.asks[0].0 + self.offset, -self.spoof.min(sell_room)));
            }
        }
        self.tick += 1;
    }
}
