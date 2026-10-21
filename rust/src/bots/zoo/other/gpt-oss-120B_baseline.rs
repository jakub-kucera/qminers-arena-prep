//! python/bots/zoo/other/gpt-oss-120B_baseline.py

use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

/// gpt-oss-120B_baseline.py: a 10-lot at the best bid and at the best ask, within the limit.
#[derive(Default)]
pub struct Baseline120 {
    which: Vec<Option<usize>>,
}

impl crate::arena::engine::Bot for Baseline120 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let limit = if self.which[product].is_some() { 50 } else { 0 };
            let position = positions[product];
            let (buy_capacity, sell_capacity) = ((limit - position).max(0), (position + limit).max(0));
            if let Some(b) = best_bid(book) {
                if buy_capacity > 0 {
                    order(out, product, b, 10.min(buy_capacity));
                }
            }
            if let Some(a) = best_ask(book) {
                if sell_capacity > 0 {
                    order(out, product, a, -(10.min(sell_capacity)));
                }
            }
        }
    }
}
