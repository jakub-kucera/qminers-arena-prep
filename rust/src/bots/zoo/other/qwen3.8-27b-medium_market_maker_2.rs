//! python/bots/zoo/other/qwen3.8-27b-medium_market_maker_2.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

#[derive(Default)]
pub struct MarketMaker2 {
    which: Vec<Option<usize>>,
    mids: Vec<Vec<f64>>,
}

impl crate::arena::engine::Bot for MarketMaker2 {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.mids = vec![Vec::new(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        let iteration = py::floordiv(tick.timestamp, 100);
        for &product in tick.order {
            let od = tick.books[product].as_ref().unwrap();
            let (Some(best_bid), Some(best_ask)) = (best_bid(od), best_ask(od)) else { continue };
            let spread = best_ask - best_bid;
            let position = positions[product];
            let limit = 50;
            let mids = &mut self.mids[product];
            mids.push((best_bid + best_ask) as f64 / 2.0);
            if mids.len() > 60 {
                mids.drain(..mids.len() - 60);
            }
            let (alpha, momentum_wt, take_threshold, mm_qty, inv_coef) = match self.which[product] {
                Some(0) => (0.06, 0.0, 5.max(spread), 6, 0.15),
                Some(1) => (0.12, 0.25, 4.max(spread), 5, 0.2),
                _ => (0.2, 0.5, 6.max(spread + 2), 4, 0.25),
            };
            let n = mids.len();
            let mut fair_value = if n == 1 {
                mids[0]
            } else {
                let mut fv = mids[n - 1];
                for i in 1..n.min(30) {
                    fv = mids[n - 1 - i] + alpha * (fv - mids[n - 1 - i]);
                }
                fv
            };
            if n >= 4 {
                let momentum = (mids[n - 1] - mids[n - n.min(5)]) / 3.min(n - 1) as f64;
                fair_value += momentum * momentum_wt;
            }
            if iteration > 9000 {
                let urgency = (iteration - 9000) as f64 / 1000.0;
                fair_value -= position as f64 * urgency * 0.5;
            }
            let adj_fv = fair_value - position as f64 * inv_coef;
            let half_spread = 1.max(py::floordiv(spread, 2));
            let mut bid_price = py::round(adj_fv - half_spread as f64);
            let mut ask_price = py::round(adj_fv + half_spread as f64);
            if bid_price >= ask_price {
                let mid_int = py::round(adj_fv);
                bid_price = mid_int - 1;
                ask_price = mid_int + 1;
            }
            bid_price = bid_price.min(best_ask - 1).max(1);
            ask_price = ask_price.max(best_bid + 1).min(999999);
            let max_buy = (limit - position).max(0);
            let max_sell = (position + limit).max(0);
            let (mut total_buy, mut total_sell) = (0, 0);
            let mut orders: Vec<(i64, i64)> = Vec::new();
            let take = take_threshold as f64;
            if best_ask as f64 <= fair_value - take && max_buy > 0 {
                let qty = mm_qty.min(max_buy);
                orders.push((best_ask, qty));
                total_buy += qty;
            }
            if best_bid as f64 >= fair_value + take && max_sell > 0 {
                let qty = mm_qty.min(max_sell);
                orders.push((best_bid, -qty));
                total_sell += qty;
            }
            if total_buy == 0 && max_buy > 0 && position < limit - 1 {
                let mut qty = mm_qty.min(max_buy);
                if position > 25 {
                    qty = 1.max(qty / 2);
                }
                if position > 40 {
                    qty = 1;
                }
                orders.push((bid_price, qty));
                total_buy += qty;
            }
            if total_sell == 0 && max_sell > 0 && position > -(limit - 1) {
                let mut qty = mm_qty.min(max_sell);
                if position < -25 {
                    qty = 1.max(qty / 2);
                }
                if position < -40 {
                    qty = 1;
                }
                orders.push((ask_price, -qty));
                total_sell += qty;
            }
            if total_buy > 0 && position + total_buy > limit {
                let excess = position + total_buy - limit;
                orders.retain(|o| o.1 < 0);
                let remaining = (total_buy - excess).max(0);
                if remaining > 0 {
                    if best_ask as f64 <= fair_value - take {
                        orders.push((best_ask, remaining));
                    } else if bid_price < best_ask {
                        orders.push((bid_price, remaining));
                    }
                }
            }
            if total_sell > 0 && position - total_sell < -limit {
                let excess = total_sell - (position + limit);
                orders.retain(|o| o.1 > 0);
                let remaining = (total_sell - excess).max(0);
                if remaining > 0 {
                    if best_bid as f64 >= fair_value + take {
                        orders.push((best_bid, -remaining));
                    } else if ask_price > best_bid {
                        orders.push((ask_price, -remaining));
                    }
                }
            }
            for (price, quantity) in orders {
                order(out, product, price, quantity);
            }
        }
    }
}
