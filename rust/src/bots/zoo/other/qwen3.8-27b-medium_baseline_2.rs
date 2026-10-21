//! python/bots/zoo/other/qwen3.8-27b-medium_baseline_2.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

fn volume(levels: &[(i64, i64)], price: i64) -> Option<i64> {
    levels.iter().find(|l| l.0 == price).map(|l| l.1)
}

#[derive(Default)]
pub struct Baseline2 {
    which: Vec<Option<usize>>,
    data: Vec<Vec<f64>>,
}

fn target_position(k: Option<usize>, prices: &[f64], mid: f64, spread: i64, timestamp: i64) -> i64 {
    let n = prices.len();
    if n < 20 {
        return 0;
    }
    let avg_win = 60.min(n);
    let rolling_avg = py::np_mean(&prices[n - avg_win..]);
    let deviation = mid - rolling_avg;
    let mom_win = 15.min(n - 1);
    let momentum = (prices[n - 1] - prices[n - 1 - mom_win]) / mom_win.max(1) as f64;
    let vol = if n >= 30 {
        let last = &prices[n - 30..];
        let changes: Vec<f64> = last.windows(2).map(|w| w[1] - w[0]).collect();
        py::np_std(&changes) + 1e-6
    } else {
        py::np_std(prices) / (n - 1).max(1) as f64 + 1e-6
    };
    let norm = vol * 3.0 + 1e-6;
    let dev_norm = deviation / norm;
    let mom_norm = (momentum * 10.0) / norm;
    let signal = match k {
        Some(0) => -1.8 * dev_norm + 0.3 * mom_norm,
        Some(1) => -1.4 * dev_norm + 0.6 * mom_norm,
        Some(_) => -1.0 * dev_norm + 1.0 * mom_norm,
        None => -1.0 * dev_norm + 0.5 * mom_norm,
    };
    let expected_move = signal.abs() * norm * 0.6;
    if expected_move < spread as f64 * 0.8 {
        return 0;
    }
    let mut target = signal * 25.0;
    if timestamp >= 999000 {
        target *= 0.2;
    } else if timestamp >= 995000 {
        target *= 0.5;
    } else if timestamp >= 990000 {
        target *= 0.75;
    }
    let target = py::round(py::max(-50.0, py::min(50.0, target)));
    if target.abs() < 2 {
        0
    } else {
        target
    }
}

impl crate::arena::engine::Bot for Baseline2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.data = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let od = tick.books[product].as_ref().unwrap();
            if let (Some(b), Some(a)) = (best_bid(od), best_ask(od)) {
                let prices = &mut self.data[product];
                prices.push((b + a) as f64 / 2.0);
                if prices.len() > 400 {
                    prices.drain(..prices.len() - 400);
                }
            }
        }
        for &product in tick.order {
            let od: &Book = tick.books[product].as_ref().unwrap();
            let (Some(best_bid), Some(best_ask)) = (best_bid(od), best_ask(od)) else { continue };
            let spread = best_ask - best_bid;
            let mid = (best_bid + best_ask) as f64 / 2.0;
            let bid_volume = volume(&od.bids, best_bid).unwrap();
            let ask_volume = volume(&od.asks, best_ask).unwrap();
            let position = positions[product];
            let prices = &self.data[product];
            if prices.len() < 20 {
                continue;
            }
            let target = target_position(self.which[product], prices, mid, spread, tick.timestamp).clamp(-50, 50);
            let diff = target - position;
            if diff > 0 {
                let qty = diff.min(50 - position).min(ask_volume);
                if qty >= 1 {
                    order(out, product, best_ask, qty);
                }
            } else if diff < 0 {
                let qty = (-diff).min(position + 50).min(bid_volume);
                if qty >= 1 {
                    order(out, product, best_bid, -qty);
                }
            }
        }
    }
}
