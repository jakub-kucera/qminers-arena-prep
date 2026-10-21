//! python/bots/zoo/other/gpt-oss-20b_baseline.py

use super::{best_ask, best_bid, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Fill, MarketTrade, OpenOrder};

/// gpt-oss-20b_baseline.py: buy one at the best ask and sell one at the best bid, every tick.
#[derive(Default)]
pub struct Baseline20;

impl crate::arena::engine::Bot for Baseline20 {
    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let position = positions[product];
            if let Some(a) = best_ask(book) {
                if position < 50 {
                    order(out, product, a, 1);
                }
            }
            if let Some(b) = best_bid(book) {
                if position > -50 {
                    order(out, product, b, -1);
                }
            }
        }
    }
}
