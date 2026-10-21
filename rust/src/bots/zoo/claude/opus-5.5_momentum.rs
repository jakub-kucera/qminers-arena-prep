//! python/bots/zoo/claude/opus-5.5_momentum.py

use super::py;
use super::{ask_wall_high, best_ask, best_bid, bid_wall_low, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const LIMITS: [i64; 3] = [50, 50, 50];
const DEFAULT_LIMIT: i64 = 20;

#[derive(Clone, Copy)]
struct P {
    fast: i64,
    slow: i64,
    vol_span: i64,
    sigma0: f64,
    sigma_floor: f64,
    entry: f64,
    exit: f64,
    stop: f64,
    warmup: i64,
}

const PARAMS: [P; 3] = [
    P { fast: 50, slow: 300, vol_span: 1000, sigma0: 0.5, sigma_floor: 0.5, entry: 3.0, exit: 0.5, stop: 1.5, warmup: 300 },
    P { fast: 100, slow: 500, vol_span: 1000, sigma0: 0.4, sigma_floor: 0.15, entry: 2.0, exit: 0.5, stop: 1.5, warmup: 300 },
    P { fast: 100, slow: 500, vol_span: 1000, sigma0: 1.5, sigma_floor: 0.3, entry: 2.0, exit: 0.5, stop: 1.5, warmup: 300 },
];
const DEFAULT_PARAMS: P = P { fast: 100, slow: 500, vol_span: 1000, sigma0: 1.0, sigma_floor: 0.3, entry: 2.0, exit: 0.5, stop: 1.5, warmup: 300 };

/// memory[product]: empty until the first price ("ef" not in mem), as Python's dict.
#[derive(Clone, Default)]
struct Mem {
    started: bool,
    ef: f64,
    es: f64,
    var: f64,
    last: f64,
    n: i64,
    reg: i64,
    peak: f64,
    blk: i64,
}

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    mem: Vec<Mem>,
}

fn update_signal(price: f64, p: &P, mem: &mut Mem) -> (f64, f64) {
    if !mem.started {
        *mem = Mem { started: true, ef: price, es: price, var: py::sq(p.sigma0), last: price, n: 0, reg: 0, peak: price, blk: 0 };
    }
    let a_f = 2.0 / (p.fast + 1) as f64;
    let a_s = 2.0 / (p.slow + 1) as f64;
    let a_v = 2.0 / (p.vol_span + 1) as f64;
    let ret = price - mem.last;
    mem.var += a_v * (ret * ret - mem.var);
    mem.ef += a_f * (price - mem.ef);
    mem.es += a_s * (price - mem.es);
    mem.last = price;
    mem.n += 1;
    let sigma = py::max(py::max(mem.var, 0.0).sqrt(), p.sigma_floor);
    let scale = sigma * ((p.slow - p.fast).max(1) as f64 / 2.0).sqrt();
    ((mem.ef - mem.es) / scale, scale)
}

fn update_regime(price: f64, z: f64, scale: f64, p: &P, mem: &mut Mem) -> i64 {
    let mut reg = mem.reg;
    if mem.blk == 1 && z < p.exit {
        mem.blk = 0;
    }
    if mem.blk == -1 && z > -p.exit {
        mem.blk = 0;
    }
    if mem.n < p.warmup {
        mem.reg = 0;
        return 0;
    }
    let stop_dist = p.stop * scale;
    if reg == 1 {
        mem.peak = py::max(mem.peak, price);
        if price < mem.peak - stop_dist {
            reg = 0;
            mem.blk = 1;
        } else if z < p.exit {
            reg = 0;
        }
    } else if reg == -1 {
        mem.peak = py::min(mem.peak, price);
        if price > mem.peak + stop_dist {
            reg = 0;
            mem.blk = -1;
        } else if z > -p.exit {
            reg = 0;
        }
    }
    if reg == 0 {
        if z > p.entry && price > mem.es && mem.blk != 1 {
            reg = 1;
            mem.peak = price;
        } else if z < -p.entry && price < mem.es && mem.blk != -1 {
            reg = -1;
            mem.peak = price;
        }
    }
    mem.reg = reg;
    reg
}

fn compact(mem: &mut Mem) {
    for v in [&mut mem.ef, &mut mem.es, &mut mem.var, &mut mem.last, &mut mem.peak] {
        *v = py::round_to(*v, 5);
    }
}

fn trade(product: usize, book: &Book, position: i64, limit: i64, p: &P, mem: &mut Mem, out: &mut Vec<Action>) {
    let (bb, ba) = (best_bid(book), best_ask(book));
    let wall_bid = (!book.bids.is_empty()).then(|| bid_wall_low(book));
    let wall_ask = (!book.asks.is_empty()).then(|| ask_wall_high(book));
    let price = if let (Some(wb), Some(wa)) = (wall_bid, wall_ask) {
        (wb + wa) as f64 / 2.0
    } else if let (Some(b), Some(a)) = (bb, ba) {
        (b + a) as f64 / 2.0
    } else if mem.started {
        mem.last
    } else {
        return;
    };
    let (z, scale) = update_signal(price, p, mem);
    let reg = update_regime(price, z, scale, p, mem);
    let target = reg * limit;
    let delta = (-limit - position).max((limit - position).min(target - position));
    if delta == 0 {
        compact(mem);
        return;
    }
    if delta > 0 {
        let mut remaining = delta;
        let cap = wall_ask.or(ba);
        let mut asks = book.asks.clone();
        asks.sort_by_key(|l| l.0);
        for (ask, vol) in asks {
            if remaining <= 0 || cap.is_none() || ask > cap.unwrap() {
                break;
            }
            let qty = remaining.min(vol);
            if qty > 0 {
                order(out, product, ask, qty);
                remaining -= qty;
            }
        }
        if remaining > 0 {
            if let Some(b) = bb {
                let mut passive = b + 1;
                if ba.is_some_and(|a| passive >= a) {
                    passive = b;
                }
                order(out, product, passive, remaining);
            }
        }
    } else {
        let mut remaining = -delta;
        let cap = wall_bid.or(bb);
        let mut bids = book.bids.clone();
        bids.sort_by(|a, b| b.0.cmp(&a.0));
        for (bid, vol) in bids {
            if remaining <= 0 || cap.is_none() || bid < cap.unwrap() {
                break;
            }
            let qty = remaining.min(vol);
            if qty > 0 {
                order(out, product, bid, -qty);
                remaining -= qty;
            }
        }
        if remaining > 0 {
            if let Some(a) = ba {
                let mut passive = a - 1;
                if bb.is_some_and(|b| passive <= b) {
                    passive = a;
                }
                order(out, product, passive, -remaining);
            }
        }
    }
    compact(mem);
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.mem = vec![Mem::default(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let (p, limit) = match self.which[product] {
                Some(k) => (PARAMS[k], LIMITS[k]),
                None => (DEFAULT_PARAMS, DEFAULT_LIMIT),
            };
            trade(product, tick.books[product].as_ref().unwrap(), positions[product], limit, &p, &mut self.mem[product], out);
        }
    }
}
