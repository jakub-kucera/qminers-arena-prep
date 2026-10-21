//! python/bots/zoo/other/qwen3.8-27b-medium_baseline.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

fn volume(levels: &[(i64, i64)], price: i64) -> Option<i64> {
    levels.iter().find(|l| l.0 == price).map(|l| l.1)
}

#[derive(Default)]
pub struct Baseline {
    which: Vec<Option<usize>>,
    mids: Vec<Vec<f64>>,
}

impl crate::arena::engine::Bot for Baseline {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.mids = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], market_trades: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        const LIMIT: i64 = 50;
        for &product in tick.order {
            let od = tick.books[product].as_ref().unwrap();
            let (Some(best_bid), Some(best_ask)) = (best_bid(od), best_ask(od)) else { continue };
            let mid = (best_bid + best_ask) as f64 / 2.0;
            let bid_vol: i64 = od.bids.iter().map(|l| l.1).sum();
            let ask_vol: i64 = od.asks.iter().map(|l| l.1).sum();
            let total_vol = bid_vol + ask_vol;
            let imbalance = if total_vol > 0 { (bid_vol - ask_vol) as f64 / total_vol as f64 } else { 0.0 };
            let mut bid_prices: Vec<i64> = od.bids.iter().map(|l| l.0).collect();
            bid_prices.sort_unstable_by(|a, b| b.cmp(a));
            let mut ask_prices: Vec<i64> = od.asks.iter().map(|l| l.0).collect();
            ask_prices.sort_unstable();
            let bid_depth: i64 = bid_prices.iter().take(3).map(|&p| volume(&od.bids, p).unwrap()).sum();
            let ask_depth: i64 = ask_prices.iter().take(3).map(|&p| volume(&od.asks, p).unwrap()).sum();
            let depth_imb = if bid_depth + ask_depth > 0 { (bid_depth - ask_depth) as f64 / (bid_depth + ask_depth) as f64 } else { 0.0 };

            let mids = &mut self.mids[product];
            mids.push(mid);
            if mids.len() > 300 {
                mids.drain(..mids.len() - 300);
            }
            let n = mids.len();
            let pos = positions[product];
            let net_flow: i64 = market_trades[product].iter().map(|t| t.quantity).sum();
            let at = |k: usize| mids[n - k];
            let mom3 = if n >= 4 { at(1) - at(4) } else if n >= 2 { at(1) - mids[0] } else { 0.0 };
            let trend = if n >= 15 { at(1) - at(15) } else if n >= 5 { at(1) - mids[0] } else { 0.0 };
            let (mean, std) = if n >= 10 {
                let window = &mids[n - 60.min(n)..];
                let mean = py::sum(window.iter().copied()) / window.len() as f64;
                let var = py::sum(window.iter().map(|&x| py::sq(x - mean))) / window.len() as f64;
                (mean, if var > 0.0 { py::powf(var, 0.5) } else { 1.0 })
            } else {
                (mid, 1.0)
            };
            let z = if std > 0.5 { (mid - mean) / std } else { 0.0 };
            let flow = net_flow as f64;
            let (mut signal, base_size) = match self.which[product] {
                Some(0) => {
                    let mut s = -z * 2.0;
                    s += -mom3 * 0.3;
                    s += imbalance * 0.8;
                    s += depth_imb * 0.5;
                    s += flow * 0.05;
                    (s, 6)
                }
                Some(1) => {
                    let mut s = mom3 * 0.6 + trend * 0.3;
                    s += imbalance * 1.2;
                    s += depth_imb * 0.8;
                    s += flow * 0.08;
                    s -= z * 0.6;
                    (s, 8)
                }
                Some(_) => {
                    let mut s = mom3 * 0.8 + trend * 0.5;
                    s += imbalance * 1.5;
                    s += depth_imb * 1.0;
                    s += flow * 0.1;
                    s -= z * 0.4;
                    if n >= 4 {
                        let moves = [at(1) - at(2), at(2) - at(3), at(3) - at(4)];
                        if moves.iter().all(|&m| m > 0.0) {
                            s += 1.0;
                        } else if moves.iter().all(|&m| m < 0.0) {
                            s -= 1.0;
                        }
                    }
                    (s, 10)
                }
                None => (mom3 * 0.5 + imbalance * 1.0, 5),
            };
            if pos >= 42 {
                signal = py::min(signal, -0.8);
            } else if pos <= -42 {
                signal = py::max(signal, 0.8);
            }
            if pos > 10 && signal < 0.0 {
                signal *= 1.4;
            } else if pos < -10 && signal > 0.0 {
                signal *= 1.4;
            }
            if signal.abs() < 0.4 {
                continue;
            }
            let size = base_size.min(2.max((signal.abs() * 2.5).trunc() as i64 + 1));
            if signal > 0.0 {
                let allowed = LIMIT - pos;
                if allowed <= 0 {
                    continue;
                }
                let size = size.min(allowed);
                if size > 0 {
                    order(out, product, best_ask, size);
                }
            } else {
                let allowed = LIMIT + pos;
                if allowed <= 0 {
                    continue;
                }
                let size = size.min(allowed);
                if size > 0 {
                    order(out, product, best_bid, -size);
                }
            }
        }
    }
}
