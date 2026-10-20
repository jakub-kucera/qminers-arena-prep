//! bots/zoo/other/deepseek-r1-14b_baseline_2.py

use super::py;
use super::{best_ask, best_bid, order};
use crate::engine::TickView;
use crate::model::{Action, Day, Fill, MarketTrade, OpenOrder};

#[derive(Default)]
pub struct Bot {
    mid_prices: Vec<Vec<f64>>, // newest first, at most 3
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.mid_prices = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let (Some(bb), Some(ba)) = (best_bid(book), best_ask(book)) else { continue };
            let mid = (bb + ba) as f64 / 2.0;
            let mids = &mut self.mid_prices[product];
            mids.insert(0, mid);
            mids.truncate(3);
            if mids.len() >= 3 {
                let ma = py::sum(mids.iter().copied()) / 3.0;
                let current = mids[0];
                let pos = positions[product];
                if current > ma {
                    let max_buy = 50 - pos;
                    if max_buy > 0 {
                        let volume = book.asks.iter().find(|l| l.0 == ba).map_or(0, |l| l.1);
                        let q = max_buy.min(volume);
                        if q > 0 {
                            order(out, product, ba, q);
                        }
                    }
                } else if current < ma {
                    let max_sell = pos;
                    if max_sell > 0 {
                        let volume = book.bids.iter().find(|l| l.0 == bb).map_or(0, |l| l.1);
                        let q = max_sell.min(volume);
                        if q > 0 {
                            order(out, product, bb, -q);
                        }
                    }
                }
            }
        }
    }
}
