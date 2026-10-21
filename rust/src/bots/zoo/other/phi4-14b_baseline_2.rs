//! python/bots/zoo/other/phi4-14b_baseline_2.py
//!
//! phi4 indexes products and book sides without checking, so a missing product or an empty side
//! raises (KeyError, ValueError, with Python's own message): the engine then drops the tick's
//! orders, and the state kept is what the Python keeps, the instance's own changes up to the
//! error, then the last traderData read over them.

use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const MIN_EMPTY: &str = "ValueError: min() iterable argument is empty";
const MAX_EMPTY: &str = "ValueError: max() iterable argument is empty";

/// Python's `KeyError` message for a missing dict key that is a product name.
fn key_error(name: &str) -> String {
    format!("KeyError: '{name}'")
}

fn lowest_bid(book: &Book) -> Option<i64> {
    book.bids.iter().map(|l| l.0).min()
}

fn highest_ask(book: &Book) -> Option<i64> {
    book.asks.iter().map(|l| l.0).max()
}

#[derive(Clone, Default)]
struct Data {
    positions: [i64; 3], // the sum of its own trades' (unsigned) quantities
    buy_prices: [Option<i64>; 3],
    sell_prices: [Option<i64>; 3],
}

#[derive(Default)]
pub struct Baseline2 {
    which: Vec<Option<usize>>,
    products: Vec<String>,
    data: Data,
    saved: Option<Data>,
    error: Option<String>,
}

impl Baseline2 {
    fn run(&mut self, tick: &TickView, own_fills: &[Fill], out: &mut Vec<Action>) -> Result<(), String> {
        for f in own_fills {
            let k = self.which[f.product].ok_or_else(|| key_error(&self.products[f.product]))?;
            self.data.positions[k] += f.quantity.abs();
        }
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let mut orders: Vec<(i64, i64)> = Vec::new();
            let k = self.which[product];
            match k {
                Some(0) => {
                    let current = self.data.positions[0];
                    if current < 10 {
                        orders.push((lowest_bid(book).ok_or(MIN_EMPTY)?, (10 - current).min(50)));
                    } else if current > 10 {
                        orders.push((highest_ask(book).ok_or(MAX_EMPTY)?, -(current - 10).min(50)));
                    }
                }
                Some(1) => {
                    let (ask, bid) = (best_ask(book).ok_or(MIN_EMPTY)?, best_bid(book).ok_or(MAX_EMPTY)?);
                    let mid = super::py::floordiv(ask + bid, 2);
                    let sell = *self.data.sell_prices[1].get_or_insert(mid);
                    let buy = *self.data.buy_prices[1].get_or_insert(mid);
                    if mid > sell {
                        orders.push((bid, 10));
                    } else if mid < buy {
                        orders.push((ask, -10));
                    }
                    self.data.sell_prices[1] = Some(sell.max(mid));
                    self.data.buy_prices[1] = Some(buy.min(mid));
                }
                Some(_) => {
                    if let (Some(top_buy), Some(top_sell)) = (best_bid(book), best_ask(book)) {
                        if top_buy > top_sell {
                            orders.push((top_sell, 10));
                            orders.push((top_buy, -10));
                        }
                    }
                }
                None => {}
            }
            // for order in orders: if it breaches, orders.remove(order): removing while iterating skips the next one
            let current = k.map_or(0, |k| self.data.positions[k]);
            let mut i = 0;
            while i < orders.len() {
                let q = orders[i].1;
                if (q > 0 && current + q > 50) || (q < 0 && current + q < -50) {
                    orders.remove(i);
                }
                i += 1;
            }
            for (price, quantity) in orders {
                order(out, product, price, quantity);
            }
        }
        Ok(())
    }
}

impl crate::arena::engine::Bot for Baseline2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &SYMBOLS);
        self.products = day.products.clone();
        self.data = Data::default();
        self.saved = None;
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, _: &[i64], own_fills: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        if let Some(saved) = &self.saved {
            self.data = saved.clone();
        }
        match self.run(tick, own_fills, out) {
            Ok(()) => self.saved = Some(self.data.clone()),
            Err(e) => self.error = Some(e),
        }
    }
}
