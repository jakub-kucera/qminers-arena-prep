//! bots/zoo/gemini/gemini-3-8-flash-high_market_maker.py

use super::py;
use super::{lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder, Price};

const POSITION_LIMIT: i64 = 50;
const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    ema: Vec<Option<f64>>, // memory["ema"][product]
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.ema = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let pos = positions[product];
            let (mut buy_capacity, mut sell_capacity) = (POSITION_LIMIT - pos, POSITION_LIMIT + pos);
            if book.bids.is_empty() && book.asks.is_empty() {
                continue;
            }
            let mut sorted_bids: Vec<(Price, i64)> = book.bids.clone();
            sorted_bids.sort_by(|a, b| b.0.cmp(&a.0));
            let mut sorted_asks: Vec<(Price, i64)> = book.asks.clone();
            sorted_asks.sort_by_key(|l| l.0);
            let best_bid = sorted_bids.first().copied();
            let best_ask = sorted_asks.first().copied();
            let (mid_price, vwap_mid) = match (best_bid, best_ask) {
                (Some((b, bv)), Some((a, av))) => ((b + a) as f64 / 2.0, (b * av + a * bv) as f64 / (bv + av) as f64),
                (Some((b, _)), None) => (b as f64, b as f64),
                (None, Some((a, _))) => (a as f64, a as f64),
                (None, None) => unreachable!(),
            };
            let k = self.which[product];
            let fair_price = match k {
                Some(0) => 10000.0,
                Some(1) => {
                    let prev_ema = self.ema[product].unwrap_or(mid_price);
                    let alpha = 0.2;
                    let current = alpha * vwap_mid + (1.0 - alpha) * prev_ema;
                    self.ema[product] = Some(current);
                    0.5 * current + 0.5 * vwap_mid
                }
                Some(_) => {
                    let prev_ema = self.ema[product].unwrap_or(mid_price);
                    let alpha = 0.35;
                    let current = alpha * vwap_mid + (1.0 - alpha) * prev_ema;
                    self.ema[product] = Some(current);
                    0.6 * vwap_mid + 0.4 * current
                }
                None => {
                    let prev_ema = self.ema[product].unwrap_or(mid_price);
                    let current = 0.25 * mid_price + 0.75 * prev_ema;
                    self.ema[product] = Some(current);
                    current
                }
            };
            let resin = k == Some(0);
            let pos_ratio = pos as f64 / POSITION_LIMIT as f64;
            let skew_mult = match k {
                Some(0) => 1.0,
                Some(2) => 2.5,
                _ => 1.5,
            };
            let adj_fair = fair_price - pos_ratio * skew_mult;
            let mut orders: Vec<(Price, i64)> = Vec::new();
            for &(ask_p, ask_v) in &sorted_asks {
                let take = if resin { ask_p < 10000 || (pos < 0 && ask_p == 10000) } else { ask_p as f64 <= adj_fair - 0.7 };
                if take && buy_capacity > 0 {
                    let qty = ask_v.min(buy_capacity);
                    orders.push((ask_p, qty));
                    buy_capacity -= qty;
                }
            }
            for &(bid_p, bid_v) in &sorted_bids {
                let take = if resin { bid_p > 10000 || (pos > 0 && bid_p == 10000) } else { bid_p as f64 >= adj_fair + 0.7 };
                if take && sell_capacity > 0 {
                    let qty = bid_v.min(sell_capacity);
                    orders.push((bid_p, -qty));
                    sell_capacity -= qty;
                }
            }
            if let (Some((best_bid, _)), Some((best_ask, _))) = (best_bid, best_ask) {
                let spread = best_ask - best_bid;
                let mut quote_bid = if resin {
                    if pos > 35 {
                        9996
                    } else if pos > 20 {
                        9997
                    } else if pos < -35 {
                        10000
                    } else if pos < -20 {
                        9999
                    } else if best_bid < 9998 {
                        9998
                    } else if spread > 1 && best_bid + 1 < 10000 {
                        best_bid + 1
                    } else {
                        9998
                    }
                } else {
                    let target_bid = py::round(adj_fair - 1.0);
                    let q = if spread > 1 {
                        if pos_ratio > 0.6 { best_bid } else { (best_bid + 1).min(target_bid) }
                    } else {
                        best_bid.min(target_bid)
                    };
                    q.min((adj_fair - 0.5).trunc() as i64)
                };
                let quote_ask = if resin {
                    if pos < -35 {
                        10004
                    } else if pos < -20 {
                        10003
                    } else if pos > 35 {
                        10000
                    } else if pos > 20 {
                        10001
                    } else if best_ask > 10002 {
                        10002
                    } else if spread > 1 && best_ask - 1 > 10000 {
                        best_ask - 1
                    } else {
                        10002
                    }
                } else {
                    let target_ask = py::round(adj_fair + 1.0);
                    let q = if spread > 1 {
                        if pos_ratio < -0.6 { best_ask } else { (best_ask - 1).max(target_ask) }
                    } else {
                        best_ask.max(target_ask)
                    };
                    q.max((adj_fair + 0.5).trunc() as i64)
                };
                if quote_bid >= quote_ask {
                    quote_bid = quote_ask - 1;
                }
                if buy_capacity > 0 {
                    orders.push((quote_bid, buy_capacity));
                }
                if sell_capacity > 0 {
                    orders.push((quote_ask, -sell_capacity));
                }
            }
            // orders_by_price, in first-seen order, then clipped to the limit
            let mut by_price: Vec<(Price, i64)> = Vec::new();
            for (p, q) in orders {
                match by_price.iter_mut().find(|(price, _)| *price == p) {
                    Some((_, total)) => *total += q,
                    None => by_price.push((p, q)),
                }
            }
            let (mut cur_buy, mut cur_sell) = (0, 0);
            let (max_buy, max_sell) = (POSITION_LIMIT - pos, POSITION_LIMIT + pos);
            for (p, q) in by_price {
                if q > 0 {
                    let allowed = q.min(max_buy - cur_buy);
                    if allowed > 0 {
                        order(out, product, p, allowed);
                        cur_buy += allowed;
                    }
                } else if q < 0 {
                    let allowed = (-q).min(max_sell - cur_sell);
                    if allowed > 0 {
                        order(out, product, p, -allowed);
                        cur_sell += allowed;
                    }
                }
            }
        }
    }
}
