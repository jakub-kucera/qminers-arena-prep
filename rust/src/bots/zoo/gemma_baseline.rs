//! bots/zoo/other/gemma4-26b_baseline.py

use super::py;
use super::{best_ask, best_bid, ids, order};
use crate::engine::TickView;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

#[derive(Default)]
pub struct Bot {
    ids: Vec<Option<usize>>,
    history: [Vec<f64>; 3],
    ema_squid: f64,
}

fn prices(book: &Book) -> (Option<i64>, Option<i64>, Option<f64>) {
    let (bb, ba) = (best_bid(book), best_ask(book));
    let mid = match (bb, ba) {
        (Some(b), Some(a)) => Some((b + a) as f64 / 2.0),
        (Some(b), None) => Some(b as f64),
        (None, Some(a)) => Some(a as f64),
        (None, None) => None,
    };
    (bb, ba, mid)
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SYMBOLS);
        self.history = Default::default();
        self.ema_squid = 0.0;
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for k in 0..3 {
            let Some(symbol) = self.ids[k] else { continue };
            let Some(book) = tick.books[symbol].as_ref() else { continue };
            let (bb, ba, mid) = prices(book);
            let Some(mid) = mid else { continue };
            let hist = &mut self.history[k];
            hist.push(mid);
            if hist.len() > 500 {
                hist.remove(0);
            }
            let pos = positions[symbol];
            let fallback = mid.trunc() as i64;
            match k {
                0 => {
                    if pos < 0 {
                        order(out, symbol, bb.unwrap_or(fallback), -pos);
                    } else if pos > 0 {
                        order(out, symbol, ba.unwrap_or(fallback), -pos);
                    }
                }
                1 => {
                    if hist.len() > 10 {
                        let (ma, std) = (py::np_mean(hist), py::np_std(hist));
                        if mid < ma - 1.5 * std {
                            if pos < 50 {
                                order(out, symbol, bb.unwrap_or(fallback), 50 - pos);
                            }
                        } else if mid > ma + 1.5 * std && pos > -50 {
                            order(out, symbol, ba.unwrap_or(fallback), -(50 + pos));
                        }
                    }
                }
                _ => {
                    let ema = if self.ema_squid == 0.0 { mid } else { 0.1 * mid + (1.0 - 0.1) * self.ema_squid };
                    self.ema_squid = ema;
                    if mid > ema && pos < 50 {
                        order(out, symbol, bb.unwrap_or(fallback), 50 - pos);
                    } else if mid < ema && pos > -50 {
                        order(out, symbol, ba.unwrap_or(fallback), -(50 + pos));
                    }
                }
            }
        }
    }
}
