//! python/bots/rivals/ in Rust: the sniper, the spoofer and the trapper, each in the file named as
//! its Python twin, and here what they share. Keep each equal to its Python file: python/tests/test_rust.py checks that both trade the
//! same, and rust/twins.json holds the hash each port was last checked against. Their constants
//! (LIMITS, DEFAULT_LIMIT, EDGE, SPOOF, OFFSET, PERIOD, BAIT, COOLDOWN) come from the Python file's
//! globals, so `--set` reaches them.

use crate::support::json::Value;
use crate::arena::model::{Action, Book, Day, OpenOrder, Order, Price};

pub(super) fn int(globals: &Value, key: &str) -> Result<i64, String> {
    globals.get(key).and_then(Value::as_i64).ok_or_else(|| format!("{key} must be an integer"))
}

/// LIMITS.get(product, DEFAULT_LIMIT), per product of the day.
pub(super) struct Limits {
    table: Vec<(String, i64)>,
    default: i64,
    pub(super) by_product: Vec<i64>,
}

impl Limits {
    pub(super) fn read(globals: &Value) -> Result<Limits, String> {
        let table = globals
            .get("LIMITS")
            .and_then(Value::as_object)
            .ok_or("LIMITS must be a dict")?
            .iter()
            .map(|(k, v)| v.as_i64().map(|v| (k.clone(), v)).ok_or_else(|| format!("LIMITS[{k}] must be an integer")))
            .collect::<Result<_, _>>()?;
        Ok(Limits { table, default: int(globals, "DEFAULT_LIMIT")?, by_product: Vec::new() })
    }

    pub(super) fn begin_day(&mut self, day: &Day) {
        self.by_product = day.products.iter().map(|p| self.table.iter().rev().find(|(k, _)| k == p).map_or(self.default, |(_, v)| *v)).collect();
    }
}

pub(super) fn cancels(product: usize, open_orders: &[OpenOrder], out: &mut Vec<Action>) {
    out.extend(open_orders.iter().filter(|o| o.product == product).map(|o| Action::Cancel(o.id)));
}

pub(super) fn ioc(product: usize, price: Price, quantity: i64) -> Action {
    Action::Order(Order { product, price, quantity, ioc: true })
}

pub(super) fn rest(product: usize, price: Price, quantity: i64) -> Action {
    Action::Order(Order { product, price, quantity, ioc: false })
}

/// The mid of the outermost levels: the market maker's walls.
pub(super) fn outer_fair(book: &Book) -> f64 {
    (book.bids[book.bids.len() - 1].0 + book.asks[book.asks.len() - 1].0) as f64 / 2.0
}

/// Takes every order through fair, and cuts inventory at fair (the spoofer's and trapper's step).
pub(super) fn take_through(product: usize, book: &Book, fair: f64, position: i64, buy_room: &mut i64, sell_room: &mut i64, out: &mut Vec<Action>) {
    for &(price, volume) in &book.bids {
        let p = price as f64;
        if *sell_room <= 0 || !(p > fair || (p >= fair && position > 0)) {
            break;
        }
        let q = volume.min(*sell_room);
        out.push(ioc(product, price, -q));
        *sell_room -= q;
    }
    for &(price, volume) in &book.asks {
        let p = price as f64;
        if *buy_room <= 0 || !(p < fair || (p <= fair && position < 0)) {
            break;
        }
        let q = volume.min(*buy_room);
        out.push(ioc(product, price, q));
        *buy_room -= q;
    }
}

pub mod sniper;
pub mod spoofer;
pub mod trapper;

pub use sniper::Sniper;
pub use spoofer::Spoofer;
pub use trapper::Trapper;
