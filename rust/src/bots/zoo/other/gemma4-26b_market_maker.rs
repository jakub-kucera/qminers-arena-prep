//! bots/zoo/other/gemma4-26b_market_maker.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
// configs: (spread, k, window); others get the default
const CONFIGS: [(f64, f64, usize); 3] = [(2.0, 0.1, 100), (6.0, 0.5, 30), (20.0, 1.5, 10)];
const DEFAULT: (f64, f64, usize) = (10.0, 1.0, 20);

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    history: Vec<Option<Vec<f64>>>,
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.history = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &symbol in tick.order {
            let book = tick.books[symbol].as_ref().unwrap();
            let (spread, k, window) = self.which[symbol].map_or(DEFAULT, |i| CONFIGS[i]);
            let pos = positions[symbol];
            let current_mid = match (best_bid(book), best_ask(book)) {
                (Some(b), Some(a)) => Some((b + a) as f64 / 2.0),
                (Some(b), None) => Some(b as f64),
                (None, Some(a)) => Some(a as f64),
                (None, None) => None,
            };
            if let Some(mid) = current_mid {
                let h = self.history[symbol].get_or_insert_with(Vec::new);
                h.push(mid);
                if h.len() > window {
                    h.drain(..h.len() - window);
                }
            }
            let fair_value = match &self.history[symbol] {
                Some(h) if !h.is_empty() => py::sum(h.iter().copied()) / h.len() as f64,
                _ => match current_mid {
                    Some(mid) => mid,
                    None => continue,
                },
            };
            let (max_buy, max_sell) = (50 - pos, -50 - pos);
            let q_bid = if pos <= 0 { 5.min(max_buy) } else { 0 };
            let q_ask = if pos >= 0 { (-5).max(max_sell) } else { 0 };
            let p_bid = py::round(fair_value - spread / 2.0 - k * pos as f64);
            let p_ask = py::round(fair_value + spread / 2.0 - k * pos as f64);
            if q_bid > 0 {
                order(out, symbol, p_bid, q_bid);
            }
            if q_ask < 0 {
                order(out, symbol, p_ask, q_ask);
            }
        }
    }
}
