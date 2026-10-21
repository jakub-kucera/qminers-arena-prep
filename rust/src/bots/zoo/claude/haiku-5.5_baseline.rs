//! python/bots/zoo/claude/haiku-5.5_baseline.py

use super::{best_ask, best_bid, ids, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const LIMIT: i64 = 50;

#[derive(Clone, Copy, PartialEq)]
enum Mode {
    Fixed(f64),
    Mid,
    Ema(f64),
}

struct Cfg {
    product: &'static str,
    mode: Mode,
    take_edge: f64,
    make_edge: f64,
    quote_size: i64,
    skew: f64,
}

// SETTINGS, in its order: the bot trades its products in this order.
const SETTINGS: [Cfg; 3] = [
    Cfg { product: "RAINFOREST_RESIN", mode: Mode::Fixed(10000.0), take_edge: 1.0, make_edge: 2.0, quote_size: 15, skew: 0.04 },
    Cfg { product: "KELP", mode: Mode::Mid, take_edge: 1.0, make_edge: 2.0, quote_size: 12, skew: 0.04 },
    Cfg { product: "SQUID_INK", mode: Mode::Ema(0.02), take_edge: 2.0, make_edge: 2.0, quote_size: 8, skew: 0.04 },
];

#[derive(Default)]
pub struct Bot {
    ids: Vec<Option<usize>>,
    store: Vec<Option<f64>>, // per SETTINGS entry
}

fn mid(book: &Book) -> Option<f64> {
    Some((best_bid(book)? + best_ask(book)?) as f64 / 2.0)
}

impl Bot {
    fn fair(&mut self, k: usize, book: &Book) -> Option<f64> {
        match SETTINGS[k].mode {
            Mode::Fixed(fair) => Some(fair),
            Mode::Mid => mid(book).or(self.store[k]),
            Mode::Ema(alpha) => match mid(book) {
                Some(m) => {
                    let fair = match self.store[k] {
                        None => m,
                        Some(prev) => prev + alpha * (m - prev),
                    };
                    self.store[k] = Some(fair);
                    Some(fair)
                }
                None => self.store[k],
            },
        }
    }
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SETTINGS.map(|c| c.product));
        self.store = vec![None; SETTINGS.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for k in 0..SETTINGS.len() {
            let Some(product) = self.ids[k] else { continue };
            let Some(book) = tick.books[product].as_ref() else { continue };
            let cfg = &SETTINGS[k];
            let Some(fair) = self.fair(k, book) else { continue };
            let pos = positions[product];
            let (bb, ba) = (best_bid(book), best_ask(book));
            let (mut buy_room, mut sell_room) = (LIMIT - pos, LIMIT + pos);
            if ba.is_some() {
                let mut asks = book.asks.clone();
                asks.sort_by_key(|l| l.0);
                for (ask, vol) in asks {
                    if ask as f64 > fair - cfg.take_edge || buy_room <= 0 {
                        break;
                    }
                    let q = vol.min(buy_room);
                    if q > 0 {
                        order(out, product, ask, q);
                        buy_room -= q;
                    }
                }
            }
            if bb.is_some() {
                let mut bids = book.bids.clone();
                bids.sort_by(|a, b| b.0.cmp(&a.0));
                for (bid, vol) in bids {
                    if (bid as f64) < fair + cfg.take_edge || sell_room <= 0 {
                        break;
                    }
                    let q = vol.min(sell_room);
                    if q > 0 {
                        order(out, product, bid, -q);
                        sell_room -= q;
                    }
                }
            }
            let skew = pos as f64 * cfg.skew;
            let mut bid_px = (fair - cfg.make_edge - skew).floor() as i64;
            let mut ask_px = (fair + cfg.make_edge - skew).ceil() as i64;
            if let Some(ba) = ba {
                bid_px = bid_px.min(ba - 1);
            }
            if let Some(bb) = bb {
                ask_px = ask_px.max(bb + 1);
            }
            if bid_px < ask_px {
                let qb = buy_room.min(cfg.quote_size);
                if qb > 0 {
                    order(out, product, bid_px, qb);
                }
                let qs = sell_room.min(cfg.quote_size);
                if qs > 0 {
                    order(out, product, ask_px, -qs);
                }
            }
        }
    }
}
