//! python/bots/zoo/other/gpt-oss-120B_market_maker.py

use super::py;
use super::{best_ask, best_bid, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

/// gpt-oss-120B_market_maker.py: the mean of the last 20 mids as fair; takes through it, quotes 2 away.
#[derive(Default)]
pub struct MarketMaker120 {
    history: Vec<Vec<f64>>,
}

impl crate::arena::engine::Bot for MarketMaker120 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.history = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let (bb, ba) = (best_bid(book), best_ask(book));
            let mid = match (bb, ba) {
                (Some(b), Some(a)) => (b + a) as f64 / 2.0,
                (Some(b), None) => b as f64,
                (None, Some(a)) => a as f64,
                (None, None) => continue,
            };
            let lst = &mut self.history[product];
            lst.push(mid);
            if lst.len() > 20 {
                lst.remove(0);
            }
            let fair = py::sum(lst.iter().copied()) / lst.len() as f64;
            let position = positions[product];
            let (can_buy, can_sell) = (50 - position, 50 + position);
            if let Some(a) = ba {
                if (a as f64) < fair && can_buy > 0 {
                    let volume = book.asks.iter().find(|l| l.0 == a).unwrap().1;
                    let qty = 20.min(can_buy).min(volume);
                    if qty > 0 {
                        order(out, product, a, qty);
                    }
                }
            }
            if let Some(b) = bb {
                if b as f64 > fair && can_sell > 0 {
                    let volume = book.bids.iter().find(|l| l.0 == b).unwrap().1;
                    let qty = 20.min(can_sell).min(volume);
                    if qty > 0 {
                        order(out, product, b, -qty);
                    }
                }
            }
            let (bid_price, ask_price) = (fair.trunc() as i64 - 2, fair.trunc() as i64 + 2);
            if can_buy > 0 && bb.is_none_or(|b| bid_price > b) {
                order(out, product, bid_price, 20.min(can_buy));
            }
            if can_sell > 0 && ba.is_none_or(|a| ask_price < a) {
                order(out, product, ask_price, -(20.min(can_sell)));
            }
        }
    }
}
