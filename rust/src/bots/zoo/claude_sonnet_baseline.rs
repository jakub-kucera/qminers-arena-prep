//! bots/zoo/claude/sonnet-5.5_baseline.py

use super::py;
use super::{lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder, Price};

const LIMIT: i64 = 50;
const BIG: i64 = 15;
const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

struct P {
    fixed: Option<f64>,
    beta: f64,
    take_edge: f64,
    min_edge: f64,
    disregard: f64,
    join: f64,
    default_edge: f64,
    clear_thresh: i64,
    max_pos: i64,
}

const PARAMS: [P; 3] = [
    P { fixed: Some(10000.0), beta: 0.0, take_edge: 1.0, min_edge: 1.0, disregard: 1.0, join: 2.0, default_edge: 4.0, clear_thresh: 0, max_pos: 50 },
    P { fixed: None, beta: -0.2, take_edge: 1.0, min_edge: 1.0, disregard: 1.0, join: 0.0, default_edge: 2.0, clear_thresh: 20, max_pos: 50 },
    P { fixed: None, beta: -0.15, take_edge: 1.5, min_edge: 1.5, disregard: 1.0, join: 0.0, default_edge: 2.5, clear_thresh: 15, max_pos: 35 },
];

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    mem: Vec<Option<f64>>, // mem[sym + "_wm"]
}

fn wall_mid(book: &Book) -> Option<f64> {
    if book.bids.is_empty() || book.asks.is_empty() {
        return None;
    }
    let bid = book.bids.iter().filter(|l| l.1 >= BIG).map(|l| l.0).max().unwrap_or_else(|| book.bids.iter().map(|l| l.0).max().unwrap());
    let ask = book.asks.iter().filter(|l| l.1 >= BIG).map(|l| l.0).min().unwrap_or_else(|| book.asks.iter().map(|l| l.0).min().unwrap());
    Some((bid + ask) as f64 / 2.0)
}

/// A dict of price -> volume left, as `bids_rem` / `asks_rem`.
struct Rem(Vec<(Price, i64)>);

impl Rem {
    fn left(&mut self, price: Price) -> &mut i64 {
        &mut self.0.iter_mut().find(|l| l.0 == price).unwrap().1
    }
}

impl Bot {
    fn trade_product(&mut self, sym: usize, book: &Book, pos: i64, prm: &P, out: &mut Vec<Action>) {
        let max_pos = prm.max_pos;
        let wm = wall_mid(book);
        let mut prev = self.mem[sym];
        if let Some(wm) = wm {
            self.mem[sym] = Some(wm);
        }
        let fair = match prm.fixed {
            Some(fixed) => fixed,
            None => {
                let wm = match wm {
                    Some(wm) => wm,
                    None => {
                        let Some(p) = prev else { return };
                        prev = None;
                        p
                    }
                };
                let mut fair = wm;
                if let Some(prev) = prev {
                    if prm.beta != 0.0 {
                        let adj = prm.beta * (wm - prev);
                        let adj = py::max(-2.0, py::min(2.0, adj));
                        fair = wm + adj;
                    }
                }
                fair
            }
        };
        let mut bids_rem = Rem(book.bids.clone());
        let mut asks_rem = Rem(book.asks.clone());
        let mut asks_sorted: Vec<Price> = book.asks.iter().map(|l| l.0).collect();
        asks_sorted.sort_unstable();
        let mut bids_sorted: Vec<Price> = book.bids.iter().map(|l| l.0).collect();
        bids_sorted.sort_unstable_by(|a, b| b.cmp(a));

        let (mut buy_cap, mut sell_cap, mut pos_eff) = (LIMIT - pos, LIMIT + pos, pos);
        let te = prm.take_edge;
        for &p in &asks_sorted {
            if fair - p as f64 >= te && buy_cap > 0 && pos_eff < max_pos {
                let q = (*asks_rem.left(p)).min(buy_cap).min((max_pos - pos_eff).max(0));
                if q > 0 {
                    order(out, sym, p, q);
                    *asks_rem.left(p) -= q;
                    buy_cap -= q;
                    pos_eff += q;
                }
            } else {
                break;
            }
        }
        for &p in &bids_sorted {
            if p as f64 - fair >= te && sell_cap > 0 && pos_eff > -max_pos {
                let q = (*bids_rem.left(p)).min(sell_cap).min((pos_eff + max_pos).max(0));
                if q > 0 {
                    order(out, sym, p, -q);
                    *bids_rem.left(p) -= q;
                    sell_cap -= q;
                    pos_eff -= q;
                }
            } else {
                break;
            }
        }
        let ct = prm.clear_thresh;
        if pos_eff > ct {
            for &p in &bids_sorted {
                if p as f64 >= fair && *bids_rem.left(p) > 0 {
                    let q = (*bids_rem.left(p)).min(pos_eff - ct).min(sell_cap);
                    if q > 0 {
                        order(out, sym, p, -q);
                        *bids_rem.left(p) -= q;
                        sell_cap -= q;
                        pos_eff -= q;
                    }
                }
                if pos_eff <= ct {
                    break;
                }
            }
        } else if pos_eff < -ct {
            for &p in &asks_sorted {
                if p as f64 <= fair && *asks_rem.left(p) > 0 {
                    let q = (*asks_rem.left(p)).min(-ct - pos_eff).min(buy_cap);
                    if q > 0 {
                        order(out, sym, p, q);
                        *asks_rem.left(p) -= q;
                        buy_cap -= q;
                        pos_eff += q;
                    }
                }
                if pos_eff >= -ct {
                    break;
                }
            }
        }
        let me = prm.min_edge;
        let bid_cap = (fair - me + 1e-9).floor() as i64;
        let ask_floor = (fair + me - 1e-9).ceil() as i64;
        let below = book.bids.iter().map(|l| l.0).filter(|&p| (p as f64) < fair - prm.disregard).max();
        let above = book.asks.iter().map(|l| l.0).filter(|&p| p as f64 > fair + prm.disregard).min();
        let mut bid = match below {
            Some(b) => if fair - b as f64 <= prm.join { b } else { b + 1 },
            None => (fair - prm.default_edge).floor() as i64,
        };
        let mut ask = match above {
            Some(a) => if a as f64 - fair <= prm.join { a } else { a - 1 },
            None => (fair + prm.default_edge).ceil() as i64,
        };
        bid = bid.min(bid_cap);
        ask = ask.max(ask_floor);
        let frac = pos_eff as f64 / max_pos as f64;
        let shift = if frac.abs() > 0.8 { 2 } else if frac.abs() > 0.4 { 1 } else { 0 };
        if pos_eff > 0 && shift != 0 {
            bid -= shift;
            ask = (ask - shift).max(fair.ceil() as i64);
        } else if pos_eff < 0 && shift != 0 {
            ask += shift;
            bid = (bid + shift).min(fair.floor() as i64);
        }
        if bid >= ask {
            bid = ask - 1;
        }
        let buy_room = buy_cap.min((max_pos - pos_eff).max(0));
        let sell_room = sell_cap.min((pos_eff + max_pos).max(0));
        if buy_room > 0 {
            order(out, sym, bid, buy_room);
        }
        if sell_room > 0 {
            order(out, sym, ask, -sell_room);
        }
    }
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.mem = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &sym in tick.order {
            let Some(k) = self.which[sym] else { continue };
            self.trade_product(sym, tick.books[sym].as_ref().unwrap(), positions[sym], &PARAMS[k], out);
        }
    }
}
