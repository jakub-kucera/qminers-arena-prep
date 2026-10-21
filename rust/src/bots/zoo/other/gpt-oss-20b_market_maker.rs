//! python/bots/zoo/other/gpt-oss-20b_market_maker.py

use super::{best_ask, best_bid, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Fill, MarketTrade, OpenOrder};

/// gpt-oss-20b_market_maker.py: a 5-lot each side at the touch (one tick away when it holds that side).
#[derive(Default)]
pub struct MarketMaker20;

impl crate::arena::engine::Bot for MarketMaker20 {
    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let pos = positions[product];
            let (max_buy, max_sell) = (50 - pos, 50 + pos);
            if let Some(a) = best_ask(book) {
                if max_buy > 0 {
                    let bid_price = if pos > 0 { (a - 1).max(0) } else { a };
                    order(out, product, bid_price, 5.min(max_buy));
                }
            }
            if let Some(b) = best_bid(book) {
                if max_sell > 0 {
                    let ask_price = (if pos < 0 { b + 1 } else { b }).max(0);
                    order(out, product, ask_price, -(5.min(max_sell)));
                }
            }
        }
    }
}
