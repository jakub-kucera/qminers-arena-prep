//! python/bots/zoo/other/phi4-14b_market_maker.py
//!
//! phi4 indexes products and book sides without checking, so a missing product or an empty side
//! raises (KeyError, ValueError, with Python's own message): the engine then drops the tick's
//! orders, and the state kept is what the Python keeps, the instance's own changes up to the
//! error, then the last traderData read over them.

use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const MIN_EMPTY: &str = "ValueError: min() iterable argument is empty";
const MAX_EMPTY: &str = "ValueError: max() iterable argument is empty";

/// Python's `KeyError` message for a missing dict key that is a product name.
fn key_error(name: &str) -> String {
    format!("KeyError: '{name}'")
}

#[derive(Default)]
pub struct MarketMaker {
    fair_values: Vec<Option<f64>>, // the instance's, kept through errors
    saved_keys: Vec<bool>,         // the products in the last traderData's fair_values
    which: Vec<Option<usize>>,     // position_limits holds only SYMBOLS
    products: Vec<String>,
    error: Option<String>,
}

impl crate::arena::engine::Bot for MarketMaker {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.fair_values = vec![None; day.products.len()];
        self.saved_keys = vec![false; day.products.len()];
        self.which = lookup(day, &SYMBOLS);
        self.products = day.products.clone();
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            // (min(order_depth.sell_orders) + max(order_depth.buy_orders)) / 2: the min first
            let (Some(ask), Some(bid)) = (best_ask(book), best_bid(book)) else {
                self.error = Some(if best_ask(book).is_none() { MIN_EMPTY } else { MAX_EMPTY }.into());
                return;
            };
            let mid = (ask + bid) as f64 / 2.0;
            self.fair_values[product] = Some(if self.saved_keys[product] { (self.fair_values[product].unwrap() + mid) / 2.0 } else { mid });
        }
        for &product in tick.order {
            if self.which[product].is_none() {
                self.error = Some(key_error(&self.products[product])); // self.position_limits[product]
                return;
            }
            let inventory = positions[product].abs();
            let fair = self.fair_values[product].unwrap().trunc() as i64;
            let (max_bid, max_ask) = (50 - inventory, 50 - (50 - inventory));
            if max_bid > 0 {
                order(out, product, fair - 1, max_bid.min(10));
            }
            if max_ask > 0 {
                order(out, product, fair + 1, -max_ask.min(10));
            }
        }
        for (k, v) in self.fair_values.iter().enumerate() {
            self.saved_keys[k] = v.is_some();
        }
    }
}
