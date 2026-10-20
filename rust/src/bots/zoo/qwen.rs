//! The four qwen3.8 bots (bots/zoo/other/qwen3.8-27b-medium_*.py), each a struct here.

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

fn volume(levels: &[(i64, i64)], price: i64) -> Option<i64> {
    levels.iter().find(|l| l.0 == price).map(|l| l.1)
}

// ---------------------------------------------------------------------------- qwen3.8-27b-medium_baseline.py

#[derive(Default)]
pub struct Baseline {
    which: Vec<Option<usize>>,
    mids: Vec<Vec<f64>>,
}

impl crate::engine::Bot for Baseline {
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

// ---------------------------------------------------------------------------- qwen3.8-27b-medium_baseline_2.py

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

impl crate::engine::Bot for Baseline2 {
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

// ---------------------------------------------------------------------------- qwen3.8-27b-medium_market_maker.py

#[derive(Default)]
pub struct MarketMaker {
    which: Vec<Option<usize>>,
    fv: Vec<Option<f64>>,
    n: Vec<i64>,
}

impl crate::engine::Bot for MarketMaker {
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

// ---------------------------------------------------------------------------- qwen3.8-27b-medium_market_maker_2.py

#[derive(Default)]
pub struct MarketMaker2 {
    which: Vec<Option<usize>>,
    mids: Vec<Vec<f64>>,
}

impl crate::engine::Bot for MarketMaker2 {
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
