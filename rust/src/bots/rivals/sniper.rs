//! python/bots/rivals/sniper.py in Rust.

use super::*;
use crate::arena::engine::{Bot, TickView};
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};
use crate::support::json::Value;

pub struct Sniper {
    limits: Limits,
    edge: f64,
}

impl Sniper {
    pub fn from_globals(globals: &Value) -> Result<Sniper, String> {
        let edge = globals.get("EDGE").and_then(Value::as_f64).ok_or("EDGE must be a number")?;
        Ok(Sniper { limits: Limits::read(globals)?, edge })
    }
}

impl Bot for Sniper {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
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
            for &(price, volume) in &book.bids {
                let p = price as f64;
                if sell_room <= 0 || !(p >= fair + self.edge || (p >= fair && position > 0)) {
                    break;
                }
                let q = volume.min(if p >= fair + self.edge { sell_room } else { sell_room.min(position) });
                out.push(ioc(product, price, -q));
                sell_room -= q;
            }
            for &(price, volume) in &book.asks {
                let p = price as f64;
                if buy_room <= 0 || !(p <= fair - self.edge || (p <= fair && position < 0)) {
                    break;
                }
                let q = volume.min(if p <= fair - self.edge { buy_room } else { buy_room.min(-position) });
                out.push(ioc(product, price, q));
                buy_room -= q;
            }
        }
    }
}
