//! The four phi4 bots (bots/zoo/other/phi4-14b_*.py), each a struct here. They index products and
//! book sides without checking, so a missing product or an empty side raises (KeyError,
//! ValueError): the engine then drops the tick's orders, and the state kept is what the Python
//! keeps, the instance's own changes up to the error, then the last traderData read over them.

use super::{best_ask, best_bid, ids, lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

fn lowest_bid(book: &Book) -> Option<i64> {
    book.bids.iter().map(|l| l.0).min()
}

fn highest_ask(book: &Book) -> Option<i64> {
    book.asks.iter().map(|l| l.0).max()
}

// ---------------------------------------------------------------------------- phi4-14b_baseline.py

/// self.state's lists that change (the rest is constant: every position it reads is 0).
#[derive(Clone, Default)]
struct BaselineState {
    kelp_last_prices: Vec<i64>,
    squid_ink_last_prices: Vec<i64>,
}

#[derive(Default)]
pub struct Baseline {
    ids: Vec<Option<usize>>,
    state: BaselineState,
    saved: Option<BaselineState>, // the last traderData returned
    error: Option<String>,
}

impl Baseline {
    fn run(&mut self, tick: &TickView, out: &mut Vec<Action>) -> Result<(), &'static str> {
        let book = |k: usize| self.ids[k].and_then(|p| tick.books[p].as_ref().map(|b| (p, b))).ok_or("KeyError");
        // Resin: its position is read from self.state, always 0, so it bids 10 at the lowest bid.
        let (resin, b) = book(0)?;
        order(out, resin, lowest_bid(b).ok_or("ValueError")?, 10);
        for (k, threshold) in [(1, None), (2, Some(5.0))] {
            let (product, b) = book(k)?;
            let (ask, bid) = (best_ask(b).ok_or("ValueError")?, best_bid(b).ok_or("ValueError")?);
            // "mid_price": the best ask's (negative) volume plus the best bid's volume
            let mid = -b.asks.iter().find(|l| l.0 == ask).unwrap().1 + b.bids.iter().find(|l| l.0 == bid).unwrap().1;
            let last = if k == 1 { &mut self.state.kelp_last_prices } else { &mut self.state.squid_ink_last_prices };
            last.push(mid);
            if last.len() > 10 {
                last.remove(0);
            }
            if last.len() == 10 {
                let mean = last.iter().sum::<i64>() as f64 / 10.0;
                let buy = match threshold {
                    None => (mid as f64) < mean,
                    Some(t) => mid as f64 - mean < -t,
                };
                if buy {
                    order(out, product, lowest_bid(b).unwrap(), 10);
                }
            }
        }
        Ok(())
    }
}

impl crate::engine::Bot for Baseline {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SYMBOLS);
        self.state = BaselineState::default();
        self.saved = None;
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, _: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        if let Some(saved) = &self.saved {
            self.state = saved.clone();
        }
        match self.run(tick, out) {
            Ok(()) => self.saved = Some(self.state.clone()),
            Err(e) => self.error = Some(e.into()),
        }
    }
}

// ---------------------------------------------------------------------------- phi4-14b_baseline_2.py

#[derive(Clone, Default)]
struct Data {
    positions: [i64; 3], // the sum of its own trades' (unsigned) quantities
    buy_prices: [Option<i64>; 3],
    sell_prices: [Option<i64>; 3],
}

#[derive(Default)]
pub struct Baseline2 {
    which: Vec<Option<usize>>,
    data: Data,
    saved: Option<Data>,
    error: Option<String>,
}

impl Baseline2 {
    fn run(&mut self, tick: &TickView, own_fills: &[Fill], out: &mut Vec<Action>) -> Result<(), &'static str> {
        for f in own_fills {
            let k = self.which[f.product].ok_or("KeyError")?;
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
                        orders.push((lowest_bid(book).ok_or("ValueError")?, (10 - current).min(50)));
                    } else if current > 10 {
                        orders.push((highest_ask(book).ok_or("ValueError")?, -(current - 10).min(50)));
                    }
                }
                Some(1) => {
                    let (ask, bid) = (best_ask(book).ok_or("ValueError")?, best_bid(book).ok_or("ValueError")?);
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

impl crate::engine::Bot for Baseline2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &SYMBOLS);
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
            Err(e) => self.error = Some(e.into()),
        }
    }
}

// ---------------------------------------------------------------------------- phi4-14b_market_maker.py

#[derive(Default)]
pub struct MarketMaker {
    fair_values: Vec<Option<f64>>, // the instance's, kept through errors
    saved_keys: Vec<bool>,         // the products in the last traderData's fair_values
    error: Option<String>,
}

impl crate::engine::Bot for MarketMaker {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.fair_values = vec![None; day.products.len()];
        self.saved_keys = vec![false; day.products.len()];
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let (Some(ask), Some(bid)) = (best_ask(book), best_bid(book)) else {
                self.error = Some("ValueError".into());
                return;
            };
            let mid = (ask + bid) as f64 / 2.0;
            self.fair_values[product] = Some(if self.saved_keys[product] { (self.fair_values[product].unwrap() + mid) / 2.0 } else { mid });
        }
        for &product in tick.order {
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

// ---------------------------------------------------------------------------- phi4-14b_market_maker_2.py

#[derive(Clone, Default)]
struct Data2 {
    inventory: Vec<Option<i64>>, // per product of the day
}

#[derive(Default)]
pub struct MarketMaker2 {
    which: Vec<Option<usize>>,
    data: Data2,
    saved: Option<Data2>,
    error: Option<String>,
}

const FAIR: [i64; 3] = [10000, 2030, 1969];

impl MarketMaker2 {
    fn run(&mut self, tick: &TickView, own_fills: &[Fill], out: &mut Vec<Action>) -> Result<(), &'static str> {
        for &product in tick.order {
            self.data.inventory[product].get_or_insert(0);
        }
        for f in own_fills {
            *self.data.inventory[f.product].as_mut().ok_or("KeyError")? += f.quantity.abs();
        }
        for &product in tick.order {
            let fair_value = FAIR[self.which[product].ok_or("KeyError")?];
            let inventory = self.data.inventory[product].unwrap();
            let (mut bid_price, mut ask_price) = (fair_value - 1, fair_value + 1);
            let (mut bid_quantity, mut ask_quantity) = (10, 10);
            if inventory > 0 {
                bid_price += super::py::floordiv(inventory, 5);
                ask_price -= super::py::floordiv(inventory, 5);
            } else if inventory < 0 {
                bid_price -= inventory.abs() / 5;
                ask_price += inventory.abs() / 5;
            }
            if inventory + ask_quantity > 50 {
                ask_quantity = 50 - inventory;
            }
            if inventory - bid_quantity < -50 {
                bid_quantity = inventory + 50;
            }
            for (price, quantity) in [(bid_price, bid_quantity), (ask_price, -ask_quantity)] {
                let valid = if quantity > 0 { inventory + quantity <= 50 } else { inventory + quantity >= -50 };
                if valid {
                    order(out, product, price, quantity);
                }
            }
        }
        Ok(())
    }
}

impl crate::engine::Bot for MarketMaker2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &SYMBOLS);
        self.data = Data2 { inventory: vec![None; day.products.len()] };
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
            Err(e) => self.error = Some(e.into()),
        }
    }
}
