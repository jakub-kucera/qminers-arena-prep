//! bots/zoo/claude/opus-5.5_baseline.py

use super::{asks_asc, ask_wall_high, best_ask, best_bid, bid_wall_low, bids_desc, lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const LIMIT: i64 = 50;
const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

struct P {
    take_edge: f64,
    make_edge: f64,
    soft: i64,
    skew_at: f64,
    reversion: f64,
}

const PARAMS: [P; 3] = [
    P { take_edge: 1.0, make_edge: 1.0, soft: 50, skew_at: 0.5, reversion: 0.0 },
    P { take_edge: 1.0, make_edge: 1.0, soft: 50, skew_at: 0.5, reversion: 0.0 },
    P { take_edge: 2.0, make_edge: 1.0, soft: 30, skew_at: 0.4, reversion: 0.2 },
];

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    last_wm: Vec<Option<f64>>, // mem[product + "_wm"]
}

fn wall_mid(book: &Book) -> Option<f64> {
    if book.bids.is_empty() || book.asks.is_empty() {
        return None;
    }
    let (mut bid, mut ask) = (bid_wall_low(book), ask_wall_high(book));
    if bid >= ask {
        bid = best_bid(book).unwrap();
        ask = best_ask(book).unwrap();
    }
    Some((bid + ask) as f64 / 2.0)
}

fn trade_product(product: usize, book: &Book, pos: i64, fair: f64, p: &P, out: &mut Vec<Action>) {
    let (mut buy_cap, mut sell_cap, mut proj) = (LIMIT - pos, LIMIT + pos, pos);
    let (asks, bids) = (asks_asc(book), bids_desc(book));
    for &(price, vol) in &asks {
        if buy_cap <= 0 || price as f64 > fair - p.take_edge {
            break;
        }
        let q = vol.min(buy_cap);
        if q > 0 {
            order(out, product, price, q);
            buy_cap -= q;
            proj += q;
        }
    }
    for &(price, vol) in &bids {
        if sell_cap <= 0 || (price as f64) < fair + p.take_edge {
            break;
        }
        let q = vol.min(sell_cap);
        if q > 0 {
            order(out, product, price, -q);
            sell_cap -= q;
            proj -= q;
        }
    }
    if proj > 0 {
        for &(price, vol) in &bids {
            if proj <= 0 || sell_cap <= 0 || (price as f64) < fair {
                break;
            }
            if (price as f64) < fair + p.take_edge {
                let q = vol.min(proj).min(sell_cap);
                if q > 0 {
                    order(out, product, price, -q);
                    sell_cap -= q;
                    proj -= q;
                }
            }
        }
    } else if proj < 0 {
        for &(price, vol) in &asks {
            if proj >= 0 || buy_cap <= 0 || price as f64 > fair {
                break;
            }
            if price as f64 > fair - p.take_edge {
                let q = vol.min(-proj).min(buy_cap);
                if q > 0 {
                    order(out, product, price, q);
                    buy_cap -= q;
                    proj += q;
                }
            }
        }
    }
    let bid_limit = (fair - p.make_edge).floor() as i64;
    let ask_limit = (fair + p.make_edge).ceil() as i64;
    let mut bid_px = match best_bid(book) {
        Some(b) => bid_limit.min(b + 1),
        None => bid_limit - 1,
    };
    let mut ask_px = match best_ask(book) {
        Some(a) => ask_limit.max(a - 1),
        None => ask_limit + 1,
    };
    let skew_level = p.skew_at * LIMIT as f64;
    if proj as f64 > skew_level {
        ask_px = (ask_px - 1).max(fair.ceil() as i64);
        bid_px -= 1;
    } else if (proj as f64) < -skew_level {
        bid_px = (bid_px + 1).min(fair.floor() as i64);
        ask_px += 1;
    }
    if bid_px >= ask_px {
        bid_px = ask_px - 1;
    }
    let buy_q = buy_cap.min((p.soft - proj).max(0));
    let sell_q = sell_cap.min((p.soft + proj).max(0));
    if buy_q > 0 {
        order(out, product, bid_px, buy_q);
    }
    if sell_q > 0 {
        order(out, product, ask_px, -sell_q);
    }
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.last_wm = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let Some(k) = self.which[product] else { continue };
            let book = tick.books[product].as_ref().unwrap();
            let fair = if k == 0 {
                10000.0
            } else {
                let last = self.last_wm[product];
                let wm = match (wall_mid(book), last) {
                    (Some(wm), _) => wm,
                    (None, Some(last)) => last,
                    (None, None) => continue,
                };
                let mut fair = wm;
                if PARAMS[k].reversion != 0.0 {
                    if let Some(last) = last {
                        fair = wm - PARAMS[k].reversion * (wm - last);
                    }
                }
                self.last_wm[product] = Some(wm);
                fair
            };
            trade_product(product, book, positions[product], fair, &PARAMS[k], out);
        }
    }
}
