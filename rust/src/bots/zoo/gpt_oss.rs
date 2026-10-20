//! The six gpt-oss bots (bots/zoo/other/gpt-oss-120B_*.py, gpt-oss-20b_*.py), each a struct here.

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

/// gpt-oss-120B_baseline.py: a 10-lot at the best bid and at the best ask, within the limit.
#[derive(Default)]
pub struct Baseline120 {
    which: Vec<Option<usize>>,
}

impl crate::engine::Bot for Baseline120 {
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

/// gpt-oss-120B_market_maker.py: the mean of the last 20 mids as fair; takes through it, quotes 2 away.
#[derive(Default)]
pub struct MarketMaker120 {
    history: Vec<Vec<f64>>,
}

impl crate::engine::Bot for MarketMaker120 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.history = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let (bb, ba) = (best_bid(book), best_ask(book));
            let mid = match (bb, ba) {
                (Some(b), Some(a)) => (b + a) as f64 / 2.0,
                (Some(b), None) => b as f64,
                (None, Some(a)) => a as f64,
                (None, None) => continue,
            };
            let lst = &mut self.history[product];
            lst.push(mid);
            if lst.len() > 20 {
                lst.remove(0);
            }
            let fair = py::sum(lst.iter().copied()) / lst.len() as f64;
            let position = positions[product];
            let (can_buy, can_sell) = (50 - position, 50 + position);
            if let Some(a) = ba {
                if (a as f64) < fair && can_buy > 0 {
                    let volume = book.asks.iter().find(|l| l.0 == a).unwrap().1;
                    let qty = 20.min(can_buy).min(volume);
                    if qty > 0 {
                        order(out, product, a, qty);
                    }
                }
            }
            if let Some(b) = bb {
                if b as f64 > fair && can_sell > 0 {
                    let volume = book.bids.iter().find(|l| l.0 == b).unwrap().1;
                    let qty = 20.min(can_sell).min(volume);
                    if qty > 0 {
                        order(out, product, b, -qty);
                    }
                }
            }
            let (bid_price, ask_price) = (fair.trunc() as i64 - 2, fair.trunc() as i64 + 2);
            if can_buy > 0 && bb.is_none_or(|b| bid_price > b) {
                order(out, product, bid_price, 20.min(can_buy));
            }
            if can_sell > 0 && ba.is_none_or(|a| ask_price < a) {
                order(out, product, ask_price, -(20.min(can_sell)));
            }
        }
    }
}

/// gpt-oss-20b_baseline.py: buy one at the best ask and sell one at the best bid, every tick.
#[derive(Default)]
pub struct Baseline20;

impl crate::engine::Bot for Baseline20 {
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

/// gpt-oss-20b_baseline_2.py: it stores the mid before reading the last one, so the move it trades
/// on is always 0 and it never trades. Its json.loads has no guard, but it only ever reads its own output.
#[derive(Default)]
pub struct Baseline20Second;

impl crate::engine::Bot for Baseline20Second {
    fn step(&mut self, _: &TickView, _: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], _: &mut Vec<Action>) {}
}

/// gpt-oss-20b_market_maker.py: a 5-lot each side at the touch (one tick away when it holds that side).
#[derive(Default)]
pub struct MarketMaker20;

impl crate::engine::Bot for MarketMaker20 {
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

/// gpt-oss-20b_market_maker_2.py: a 5-lot a tick either side of the integer mid, within [-20, 20].
#[derive(Default)]
pub struct MarketMaker20Second;

impl crate::engine::Bot for MarketMaker20Second {
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
