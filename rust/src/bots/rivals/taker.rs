//! python/bots/rivals/taker.py in Rust.

use super::*;
use crate::arena::engine::{Bot, TickView};
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};
use crate::support::json::Value;

pub struct Taker {
    limits: Limits,
    rate: f64,
    noise: f64,
    size: i64,
    hold: i64,
    seed: u64,
    names: Vec<u64>,         // per product: FNV-1a of its name
    last: Vec<Option<f64>>, // per product: the last tick's mid
}

impl Taker {
    pub fn from_globals(globals: &Value) -> Result<Taker, String> {
        let float = |key: &str| globals.get(key).and_then(Value::as_f64).ok_or_else(|| format!("{key} must be a number"));
        Ok(Taker {
            limits: Limits::read(globals)?,
            rate: float("RATE")?,
            noise: float("NOISE")?,
            size: int(globals, "SIZE")?,
            hold: int(globals, "HOLD")?,
            seed: int(globals, "SEED")? as u64,
            names: Vec::new(),
            last: Vec::new(),
        })
    }

    /// taker.py's `draw`: splitmix64's finalizer over the name's hash, SEED, the timestamp and k.
    fn draw(&self, timestamp: i64, product: usize, k: u64) -> f64 {
        let mut x = self.names[product] ^ self.seed.wrapping_mul(0x9E3779B97F4A7C15) ^ (timestamp as u64).wrapping_mul(0xBF58476D1CE4E5B9) ^ k;
        x = x.wrapping_add(0x9E3779B97F4A7C15);
        x = (x ^ (x >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        x = (x ^ (x >> 27)).wrapping_mul(0x94D049BB133111EB);
        x ^= x >> 31;
        (x >> 11) as f64 / 9007199254740992.0
    }
}

fn fnv1a(text: &str) -> u64 {
    text.bytes().fold(0xCBF29CE484222325, |h, b| (h ^ b as u64).wrapping_mul(0x100000001B3))
}

impl Bot for Taker {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
        self.names = day.products.iter().map(|p| fnv1a(p)).collect();
        self.last = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            cancels(product, open_orders, out);
            let book = tick.books[product].as_ref().unwrap();
            if book.bids.is_empty() || book.asks.is_empty() {
                continue;
            }
            let limit = self.limits.by_product[product];
            let (bid, ask) = (book.bids[0], book.asks[0]);
            let mid = (bid.0 + ask.0) as f64 / 2.0;
            let last = self.last[product].replace(mid);
            let (u, v) = (self.draw(tick.timestamp, product, 0), self.draw(tick.timestamp, product, 1));
            let position = positions[product];
            let side = if position >= self.hold {
                -1
            } else if position <= -self.hold {
                1
            } else if u < self.rate {
                let moved = last.map_or(0.0, |l| mid - l);
                if moved > 0.0 || (moved == 0.0 && v < 0.5) { 1 } else { -1 }
            } else if u < self.rate + self.noise {
                if v < 0.5 { 1 } else { -1 }
            } else {
                0
            };
            if side > 0 {
                let q = self.size.min(ask.1).min(limit - position);
                if q > 0 {
                    out.push(ioc(product, ask.0, q));
                }
            } else if side < 0 {
                let q = self.size.min(bid.1).min(limit + position);
                if q > 0 {
                    out.push(ioc(product, bid.0, -q));
                }
            }
        }
    }
}
