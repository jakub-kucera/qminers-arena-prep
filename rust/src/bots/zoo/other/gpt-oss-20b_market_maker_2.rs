//! python/bots/zoo/other/gpt-oss-20b_market_maker_2.py

use super::py;
use super::{best_ask, best_bid, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Fill, MarketTrade, OpenOrder};

/// gpt-oss-20b_market_maker_2.py: a 5-lot a tick either side of the integer mid, within [-20, 20].
#[derive(Default)]
pub struct MarketMaker20Second;

impl crate::arena::engine::Bot for MarketMaker20Second {
    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        const MAX_POS: i64 = 50;
        const QUANTITY: i64 = 5;
        for &symbol in tick.order {
            let book = tick.books[symbol].as_ref().unwrap();
            let (Some(b), Some(a)) = (best_bid(book), best_ask(book)) else { continue };
            let mid = py::floordiv(b + a, 2);
            let (bid_price, ask_price) = (mid - 1, mid + 1);
            let pos = positions[symbol];
            let mut orders = Vec::new();
            if pos < 20 && pos + QUANTITY <= MAX_POS {
                orders.push((bid_price, QUANTITY));
            }
            if pos > -20 && pos - QUANTITY >= -MAX_POS {
                orders.push((ask_price, -QUANTITY));
            }
            let total_buy: i64 = orders.iter().filter(|o| o.1 > 0).map(|o| o.1).sum();
            let total_sell: i64 = orders.iter().filter(|o| o.1 < 0).map(|o| -o.1).sum();
            if (total_buy > 0 && pos + total_buy > MAX_POS) || (total_sell > 0 && pos - total_sell < -MAX_POS) {
                orders.clear();
            }
            for (price, quantity) in orders {
                order(out, symbol, price, quantity);
            }
        }
    }
}
