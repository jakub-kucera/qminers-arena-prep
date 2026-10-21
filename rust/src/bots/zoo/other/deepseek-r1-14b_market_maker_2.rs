//! bots/zoo/other/deepseek-r1-14b_market_maker_2.py

use super::{best_ask, best_bid, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Fill, MarketTrade, OpenOrder};

#[derive(Default)]
pub struct Bot;

impl crate::arena::engine::Bot for Bot {
    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let current_pos = positions[product];
            let (max_buy, max_sell) = (50 - current_pos, -50 - current_pos);
            let quantity_buy = if max_buy > 0 { max_buy } else { 0 };
            let quantity_sell = if max_sell < 0 { -max_sell } else { 0 };
            if let (Some(b), Some(a)) = (best_bid(book), best_ask(book)) {
                let mid = (b + a) as f64 / 2.0;
                if quantity_buy > 0 {
                    order(out, product, (mid - 1.0).trunc() as i64, quantity_buy);
                }
                if quantity_sell > 0 {
                    order(out, product, (mid + 1.0).trunc() as i64, -quantity_sell);
                }
            }
        }
    }
}
