//! bots/zoo/other/gemma4-26b_baseline_2.py
//!
//! It reads state.order_depths[symbol] for all three P3 round 1 products without checking, so a
//! day without one of them raises KeyError every tick (no orders, traderData kept).

use super::py;
use super::{best_ask, best_bid, ids, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

#[derive(Default)]
pub struct Bot {
    ids: Vec<Option<usize>>,
    prices: [Vec<f64>; 3],
    error: Option<String>,
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SYMBOLS);
        self.prices = Default::default();
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        let books: Option<Vec<usize>> = self.ids.iter().map(|id| id.filter(|&k| tick.books[k].is_some())).collect();
        let Some(symbols) = books else {
            let missing = self.ids.iter().position(|id| id.filter(|&k| tick.books[k].is_some()).is_none()).unwrap();
            self.error = Some(format!("KeyError: '{}'", SYMBOLS[missing]));
            return;
        };
        for (k, &symbol) in symbols.iter().enumerate() {
            let book = tick.books[symbol].as_ref().unwrap();
            if let (Some(b), Some(a)) = (best_bid(book), best_ask(book)) {
                let prices = &mut self.prices[k];
                prices.push((b + a) as f64 / 2.0);
                if prices.len() > 200 {
                    prices.remove(0);
                }
            }
        }
        for (k, &symbol) in symbols.iter().enumerate() {
            let prices = &self.prices[k];
            if prices.is_empty() {
                continue;
            }
            let book = tick.books[symbol].as_ref().unwrap();
            let (bid0, ask0) = (best_bid(book), best_ask(book));
            let current_pos = positions[symbol];
            let aggressive = |target_pos: i64, out: &mut Vec<Action>| {
                let diff = target_pos - current_pos;
                if diff > 0 {
                    if let Some(a) = ask0 {
                        let qty = diff.min(50 - current_pos);
                        if qty > 0 {
                            order(out, symbol, a, qty);
                        }
                    }
                } else if diff < 0 {
                    if let Some(b) = bid0 {
                        let qty = diff.max(-50 - current_pos);
                        if qty < 0 {
                            order(out, symbol, b, qty);
                        }
                    }
                }
            };
            match k {
                0 => {
                    if current_pos > 0 {
                        if let Some(b) = bid0 {
                            order(out, symbol, b, -current_pos.min(50));
                        }
                    } else if current_pos < 0 {
                        if let Some(a) = ask0 {
                            order(out, symbol, a, current_pos.abs().min(50));
                        }
                    } else if let (Some(b), Some(a)) = (bid0, ask0) {
                        order(out, symbol, b, 5);
                        order(out, symbol, a, -5);
                    }
                }
                1 => {
                    if prices.len() >= 30 {
                        let short = py::np_mean(&prices[prices.len() - 10..]);
                        let long = py::np_mean(&prices[prices.len() - 30..]);
                        let target = if short > long { 50 } else if short < long { -50 } else { 0 };
                        aggressive(target, out);
                    }
                }
                _ => {
                    if prices.len() >= 20 {
                        let last = &prices[prices.len() - 20..];
                        let (avg, std) = (py::np_mean(last), py::np_std(last));
                        if std > 0.0 {
                            let z = (prices[prices.len() - 1] - avg) / std;
                            let target = if z > 1.5 { -50 } else if z < -1.5 { 50 } else { 0 };
                            aggressive(target, out);
                        }
                    } else if let (Some(b), Some(a)) = (bid0, ask0) {
                        order(out, symbol, b, 5);
                        order(out, symbol, a, -5);
                    }
                }
            }
        }
    }
}
