//! python/bots/zoo/other/qwen3.8-27b-medium_market_maker.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

fn volume(levels: &[(i64, i64)], price: i64) -> Option<i64> {
    levels.iter().find(|l| l.0 == price).map(|l| l.1)
}

#[derive(Default)]
pub struct MarketMaker {
    which: Vec<Option<usize>>,
    fv: Vec<Option<f64>>,
    n: Vec<i64>,
}

impl crate::arena::engine::Bot for MarketMaker {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.fv = vec![None; day.products.len()];
        self.n = vec![0; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let od = tick.books[product].as_ref().unwrap();
            if od.bids.is_empty() && od.asks.is_empty() {
                continue;
            }
            let bb = best_bid(od).unwrap_or(0);
            let ba = best_ask(od);
            let mid = if bb > 0 && ba.is_some_and(|a| a > bb) {
                (bb + ba.unwrap()) as f64 / 2.0
            } else if bb > 0 {
                bb as f64
            } else if let Some(a) = ba {
                a as f64
            } else {
                continue;
            };
            self.n[product] += 1;
            let n = self.n[product];
            let fv = match self.fv[product] {
                None => mid,
                Some(old) => {
                    let mut alpha = match self.which[product] {
                        Some(0) => 0.02,
                        Some(1) => 0.04,
                        Some(_) => 0.08,
                        None => 0.05,
                    };
                    if n < 20 {
                        alpha = py::max(alpha, 0.2);
                    }
                    alpha * mid + (1.0 - alpha) * old
                }
            };
            self.fv[product] = Some(fv);
            let pos = positions[product];
            let lim = 50;
            let (base_qty, make_thresh, take_thresh) = match self.which[product] {
                Some(0) => (8, 3.0, 4.0),
                Some(1) => (5, 4.0, 5.0),
                _ => (3, 5.0, 6.0),
            };
            let inv_ratio = pos as f64 / lim as f64;
            let size_factor = py::max(0.2, 1.0 - inv_ratio.abs() * 0.7);
            let adj_qty = 1.max((base_qty as f64 * size_factor).trunc() as i64);
            let mut make_bid_ok = bb as f64 <= fv + make_thresh;
            let mut make_ask_ok = ba.is_some_and(|a| a as f64 >= fv - make_thresh);
            if pos as f64 > lim as f64 * 0.6 {
                make_bid_ok = false;
            }
            if (pos as f64) < -(lim as f64) * 0.6 {
                make_ask_ok = false;
            }
            if pos >= lim - 1 {
                make_bid_ok = false;
            }
            if pos <= -lim + 1 {
                make_ask_ok = false;
            }
            let mut make_bid_qty = if make_bid_ok { adj_qty } else { 0 };
            let mut make_ask_qty = if make_ask_ok { adj_qty } else { 0 };
            let (mut take_buy_qty, mut take_buy_price, mut take_sell_qty, mut take_sell_price) = (0, 0, 0, 0);
            if let Some(a) = ba {
                if (a as f64) < fv - take_thresh {
                    let avail = volume(&od.asks, a).unwrap_or(1);
                    let room = (lim - pos - make_bid_qty).max(0);
                    take_buy_qty = adj_qty.min(avail).min(room);
                    if take_buy_qty > 0 {
                        take_buy_price = a;
                    }
                }
            }
            if bb as f64 > fv + take_thresh {
                let avail = volume(&od.bids, bb).unwrap_or(1);
                let room = (pos + lim - make_ask_qty).max(0);
                take_sell_qty = adj_qty.min(avail).min(room);
                if take_sell_qty > 0 {
                    take_sell_price = bb;
                }
            }
            let total_buy = make_bid_qty + take_buy_qty;
            let total_sell = make_ask_qty + take_sell_qty;
            if pos + total_buy > lim {
                let excess = pos + total_buy - lim;
                take_buy_qty = (take_buy_qty - excess).max(0);
                let excess = pos + make_bid_qty + take_buy_qty - lim;
                if excess > 0 {
                    make_bid_qty = (make_bid_qty - excess).max(0);
                }
            }
            if pos - total_sell < -lim {
                let excess = -(pos - total_sell) - lim;
                take_sell_qty = (take_sell_qty - excess).max(0);
                let excess = -(pos - make_ask_qty - take_sell_qty) - lim;
                if excess > 0 {
                    make_ask_qty = (make_ask_qty - excess).max(0);
                }
            }
            if make_bid_qty > 0 && bb > 0 {
                order(out, product, bb, make_bid_qty);
            }
            if make_ask_qty > 0 && ba.is_some_and(|a| a > 0) {
                order(out, product, ba.unwrap(), -make_ask_qty);
            }
            if take_buy_qty > 0 && take_buy_price > 0 {
                order(out, product, take_buy_price, take_buy_qty);
            }
            if take_sell_qty > 0 && take_sell_price > 0 {
                order(out, product, take_sell_price, -take_sell_qty);
            }
        }
    }
}
