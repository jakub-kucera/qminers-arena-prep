//! python/bots/zoo/other/phi4-14b_market_maker_2.py
//!
//! phi4 indexes products and book sides without checking, so a missing product or an empty side
//! raises (KeyError, ValueError, with Python's own message): the engine then drops the tick's
//! orders, and the state kept is what the Python keeps, the instance's own changes up to the
//! error, then the last traderData read over them.

use super::{lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

/// Python's `KeyError` message for a missing dict key that is a product name.
fn key_error(name: &str) -> String {
    format!("KeyError: '{name}'")
}

#[derive(Clone, Default)]
struct Data2 {
    inventory: Vec<Option<i64>>, // per product of the day
}

#[derive(Default)]
pub struct MarketMaker2 {
    which: Vec<Option<usize>>,
    products: Vec<String>,
    data: Data2,
    saved: Option<Data2>,
    error: Option<String>,
}

const FAIR: [i64; 3] = [10000, 2030, 1969];

impl MarketMaker2 {
    fn run(&mut self, tick: &TickView, own_fills: &[Fill], out: &mut Vec<Action>) -> Result<(), String> {
        for &product in tick.order {
            self.data.inventory[product].get_or_insert(0);
        }
        for f in own_fills {
            *self.data.inventory[f.product].as_mut().ok_or_else(|| key_error(&self.products[f.product]))? += f.quantity.abs();
        }
        for &product in tick.order {
            let fair_value = FAIR[self.which[product].ok_or_else(|| key_error(&self.products[product]))?];
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

impl crate::arena::engine::Bot for MarketMaker2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &SYMBOLS);
        self.products = day.products.clone();
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
            Err(e) => self.error = Some(e),
        }
    }
}
