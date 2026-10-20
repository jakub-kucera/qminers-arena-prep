//! bots/zoo/claude/opus-5.5_mean_reversion.py

use super::py;
use super::{asks_asc, ask_wall_high, best_ask, best_bid, bid_wall_low, bids_desc, lookup, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder, Price};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const LIMITS: [i64; 3] = [50, 50, 50];

enum Cfg {
    Mm { window: usize, prior: Option<f64>, use_mean: bool, take_edge: f64, make_edge: f64, skew: f64, revert: f64 },
    Mr { window: usize, min_hist: usize, entry: f64, exit: f64, min_std: f64, mm_size: i64, band: i64 },
}

const CFG: [Cfg; 3] = [
    Cfg::Mm { window: 200, prior: Some(10000.0), use_mean: true, take_edge: 1.0, make_edge: 1.0, skew: 0.0, revert: 0.0 },
    Cfg::Mm { window: 20, prior: None, use_mean: false, take_edge: 1.0, make_edge: 1.0, skew: 1.0, revert: 0.2 },
    Cfg::Mr { window: 150, min_hist: 50, entry: 2.2, exit: 0.3, min_std: 2.0, mm_size: 8, band: 15 },
];

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    hists: Vec<Vec<f64>>,
    targets: Vec<i64>,
    prevs: Vec<Option<f64>>,
}

fn wall_mid(book: &Book) -> Option<f64> {
    match (book.bids.is_empty(), book.asks.is_empty()) {
        (false, false) => {
            let (bw, aw) = (bid_wall_low(book), ask_wall_high(book));
            if bw < aw {
                Some((bw + aw) as f64 / 2.0)
            } else {
                Some((best_bid(book).unwrap() + best_ask(book).unwrap()) as f64 / 2.0)
            }
        }
        (false, true) => Some(best_bid(book).unwrap() as f64),
        (true, false) => Some(best_ask(book).unwrap() as f64),
        (true, true) => None,
    }
}

fn mean_std(xs: &[f64]) -> (f64, f64) {
    let n = xs.len();
    let m = py::sum(xs.iter().copied()) / n as f64;
    if n < 2 {
        return (m, 0.0);
    }
    let v = py::sum(xs.iter().map(|&x| py::sq(x - m))) / (n - 1) as f64;
    (m, v.sqrt())
}

struct OrderBuilder<'a> {
    product: usize,
    pos: i64,
    limit: i64,
    buy_room: i64,
    sell_room: i64,
    bought: i64,
    sold: i64,
    out: &'a mut Vec<Action>,
}

impl OrderBuilder<'_> {
    fn live(&self) -> i64 {
        self.pos + self.bought - self.sold
    }

    fn buy(&mut self, price: Price, qty: i64) -> i64 {
        let qty = qty.min(self.buy_room - self.bought);
        if qty > 0 {
            order(self.out, self.product, price, qty);
            self.bought += qty;
        }
        qty
    }

    fn sell(&mut self, price: Price, qty: i64) -> i64 {
        let qty = qty.min(self.sell_room - self.sold);
        if qty > 0 {
            order(self.out, self.product, price, -qty);
            self.sold += qty;
        }
        qty
    }
}

fn market_make(ob: &mut OrderBuilder, book: &Book, fair: f64, take_edge: f64, make_edge: f64, skew: f64) {
    let (asks, bids) = (asks_asc(book), bids_desc(book));
    for &(p, v) in &asks {
        if p as f64 <= fair - take_edge {
            ob.buy(p, v);
        } else if p as f64 <= fair && ob.live() < 0 {
            let q = v.min(-ob.live());
            ob.buy(p, q);
        } else {
            break;
        }
    }
    for &(p, v) in &bids {
        if p as f64 >= fair + take_edge {
            ob.sell(p, v);
        } else if p as f64 >= fair && ob.live() > 0 {
            let q = v.min(ob.live());
            ob.sell(p, q);
        } else {
            break;
        }
    }
    let rfair = fair - skew * ob.live() as f64 / ob.limit as f64;
    let bid_cap = (rfair - make_edge + 1e-9).floor() as i64;
    let ask_floor = (rfair + make_edge - 1e-9).ceil() as i64;
    let bid_px = bids.iter().find(|&&(p, _)| p + 1 <= bid_cap).map_or(bid_cap - 1, |&(p, _)| p + 1).min(bid_cap);
    let ask_px = asks.iter().find(|&&(p, _)| p - 1 >= ask_floor).map_or(ask_floor + 1, |&(p, _)| p - 1).max(ask_floor);
    if bid_px >= ask_px {
        return;
    }
    let q = ob.buy_room - ob.bought;
    ob.buy(bid_px, q);
    let q = ob.sell_room - ob.sold;
    ob.sell(ask_px, q);
}

#[allow(clippy::too_many_arguments)]
fn mean_reversion(ob: &mut OrderBuilder, book: &Book, wm: f64, hist: &[f64], prev_target: i64, window: usize, min_hist: usize, entry: f64, exit: f64,
                  min_std: f64, mm_size: i64, band: i64) -> i64 {
    let l = ob.limit;
    let mut target = prev_target;
    if hist.len() >= min_hist {
        let (m, s) = mean_std(&hist[hist.len().saturating_sub(window)..]);
        let s = py::max(s, min_std);
        let z = (wm - m) / s;
        if z >= entry {
            target = -l;
        } else if z <= -entry {
            target = l;
        } else if z.abs() <= exit {
            target = 0;
        } else if target > 0 && z >= 0.0 {
            target = 0;
        } else if target < 0 && z <= 0.0 {
            target = 0;
        }
    } else {
        target = 0;
    }
    let (asks, bids) = (asks_asc(book), bids_desc(book));
    let mut diff = target - ob.live();
    if diff > 0 {
        for &(p, v) in &asks {
            if diff <= 0 {
                break;
            }
            diff -= ob.buy(p, v.min(diff));
        }
    } else if diff < 0 {
        let mut need = -diff;
        for &(p, v) in &bids {
            if need <= 0 {
                break;
            }
            need -= ob.sell(p, v.min(need));
        }
    }
    if bids.is_empty() || asks.is_empty() {
        return target;
    }
    let bid_px = (bids[0].0 + 1).min((wm - 1.0 + 1e-9).floor() as i64);
    let ask_px = (asks[0].0 - 1).max((wm + 1.0 - 1e-9).ceil() as i64);
    if bid_px >= ask_px {
        return target;
    }
    let live = ob.live();
    let want_buy = (target - live).max(0);
    let want_sell = (live - target).max(0);
    let bq = want_buy + if live < target + band { mm_size } else { 0 };
    let sq = want_sell + if live > target - band { mm_size } else { 0 };
    if bq > 0 {
        ob.buy(bid_px, bq);
    }
    if sq > 0 {
        ob.sell(ask_px, sq);
    }
    target
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        let n = day.products.len();
        self.which = lookup(day, &PRODUCTS);
        self.hists = vec![Vec::new(); n];
        self.targets = vec![0; n];
        self.prevs = vec![None; n];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let Some(k) = self.which[product] else { continue };
            let book = tick.books[product].as_ref().unwrap();
            let limit = LIMITS[k];
            let pos = positions[product];
            let Some(wm) = wall_mid(book) else { continue };
            let hist = &mut self.hists[product];
            hist.push(py::round_to(wm, 1));
            let window = match CFG[k] {
                Cfg::Mm { window, .. } | Cfg::Mr { window, .. } => window,
            };
            if hist.len() > window {
                hist.drain(..hist.len() - window);
            }
            let mut ob = OrderBuilder { product, pos, limit, buy_room: limit - pos, sell_room: limit + pos, bought: 0, sold: 0, out };
            match CFG[k] {
                Cfg::Mm { prior, use_mean, take_edge, make_edge, skew, revert, .. } => {
                    let fair = if use_mean {
                        if hist.len() >= 20 {
                            let (m, _) = mean_std(hist);
                            py::round(m) as f64
                        } else {
                            prior.unwrap()
                        }
                    } else {
                        let prev = self.prevs[product].unwrap_or(wm);
                        wm - revert * (wm - prev)
                    };
                    self.prevs[product] = Some(wm);
                    market_make(&mut ob, book, fair, take_edge, make_edge, skew);
                }
                Cfg::Mr { window, min_hist, entry, exit, min_std, mm_size, band } => {
                    let t = mean_reversion(&mut ob, book, wm, hist, self.targets[product], window, min_hist, entry, exit, min_std, mm_size, band);
                    self.targets[product] = t;
                }
            }
        }
    }
}
