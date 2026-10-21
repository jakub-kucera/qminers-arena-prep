//! bots/zoo/other/deepseek-r1-14b_market_maker.py

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
            let (bb, ba) = (best_bid(book), best_ask(book));
            let mid = match (bb, ba) {
                (Some(b), Some(a)) => (b + a) as f64 / 2.0,
                _ => 0.0,
            };
            let bid_price = (mid - 0.5).trunc() as i64;
            let ask_price = (mid + 0.5).trunc() as i64;
            let (max_buy, max_sell) = (50 - current_pos, current_pos + 50);
            let mut buy_qty = 0;
            if bb.is_none_or(|b| bid_price > b) && max_buy > 0 {
                buy_qty = max_buy.min(1);
            }
            let mut sell_qty = 0;
            if ba.is_none_or(|a| ask_price < a) && max_sell > 0 {
                sell_qty = max_sell.min(1);
            }
            let new_pos = current_pos + buy_qty - sell_qty;
            if buy_qty > 0 && new_pos <= 50 {
                order(out, product, bid_price, buy_qty);
            }
            if sell_qty > 0 && new_pos >= -50 {
                order(out, product, ask_price, -sell_qty);
            }
        }
    }
}
