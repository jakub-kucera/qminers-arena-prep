//! python/bots/zoo/other/phi4-14b_baseline.py
//!
//! phi4 indexes products and book sides without checking, so a missing product or an empty side
//! raises (KeyError, ValueError, with Python's own message): the engine then drops the tick's
//! orders, and the state kept is what the Python keeps, the instance's own changes up to the
//! error, then the last traderData read over them.

use super::{best_ask, best_bid, ids, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const MISSING: [&str; 3] = ["KeyError: 'RAINFOREST_RESIN'", "KeyError: 'KELP'", "KeyError: 'SQUID_INK'"];
const MIN_EMPTY: &str = "ValueError: min() iterable argument is empty";
const MAX_EMPTY: &str = "ValueError: max() iterable argument is empty";

fn lowest_bid(book: &Book) -> Option<i64> {
    book.bids.iter().map(|l| l.0).min()
}

/// self.state's lists that change (the rest is constant: every position it reads is 0).
#[derive(Clone, Default)]
struct BaselineState {
    kelp_last_prices: Vec<i64>,
    squid_ink_last_prices: Vec<i64>,
}

#[derive(Default)]
pub struct Baseline {
    ids: Vec<Option<usize>>,
    state: BaselineState,
    saved: Option<BaselineState>, // the last traderData returned
    error: Option<String>,
}

impl Baseline {
    fn run(&mut self, tick: &TickView, out: &mut Vec<Action>) -> Result<(), &'static str> {
        let book = |k: usize| self.ids[k].and_then(|p| tick.books[p].as_ref().map(|b| (p, b))).ok_or(MISSING[k]);
        // Resin: its position is read from self.state, always 0, so it bids 10 at the lowest bid.
        let (resin, b) = book(0)?;
        order(out, resin, lowest_bid(b).ok_or(MIN_EMPTY)?, 10);
        for (k, threshold) in [(1, None), (2, Some(5.0))] {
            let (product, b) = book(k)?;
            let (ask, bid) = (best_ask(b).ok_or(MIN_EMPTY)?, best_bid(b).ok_or(MAX_EMPTY)?);
            // "mid_price": the best ask's (negative) volume plus the best bid's volume
            let mid = -b.asks.iter().find(|l| l.0 == ask).unwrap().1 + b.bids.iter().find(|l| l.0 == bid).unwrap().1;
            let last = if k == 1 { &mut self.state.kelp_last_prices } else { &mut self.state.squid_ink_last_prices };
            last.push(mid);
            if last.len() > 10 {
                last.remove(0);
            }
            if last.len() == 10 {
                let mean = last.iter().sum::<i64>() as f64 / 10.0;
                let buy = match threshold {
                    None => (mid as f64) < mean,
                    Some(t) => mid as f64 - mean < -t,
                };
                if buy {
                    order(out, product, lowest_bid(b).unwrap(), 10);
                }
            }
        }
        Ok(())
    }
}

impl crate::arena::engine::Bot for Baseline {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SYMBOLS);
        self.state = BaselineState::default();
        self.saved = None;
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, _: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        if let Some(saved) = &self.saved {
            self.state = saved.clone();
        }
        match self.run(tick, out) {
            Ok(()) => self.saved = Some(self.state.clone()),
            Err(e) => self.error = Some(e.into()),
        }
    }
}
