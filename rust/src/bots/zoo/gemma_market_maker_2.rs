//! bots/zoo/other/gemma4-26b_market_maker_2.py

use super::py;
use super::{best_ask, best_bid, ids, order};
use crate::engine::TickView;
use crate::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const SYMBOLS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const FALLBACK: [f64; 3] = [10000.0, 2030.0, 1970.0];
const ALPHA: [f64; 3] = [0.05, 0.15, 0.3];
const VOL_MULT: [f64; 3] = [0.5, 1.2, 2.5];

#[derive(Default)]
pub struct Bot {
    ids: Vec<Option<usize>>,
    history: [Vec<f64>; 3],
    products: usize, // the day's; index products + k is SYMBOLS[k] when the day lacks it
}

impl crate::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.ids = ids(day, &SYMBOLS);
        self.history = Default::default();
        self.products = day.products.len();
    }

    fn product_name(&self, product: usize) -> Option<String> {
        SYMBOLS.get(product.checked_sub(self.products)?).map(|s| s.to_string())
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for k in 0..3 {
            let id = self.ids[k];
            let book = id.and_then(|p| tick.books[p].as_ref());
            let mut mid = book.and_then(|b| match (best_bid(b), best_ask(b)) {
                (Some(bb), Some(ba)) => Some((bb + ba) as f64 / 2.0),
                (Some(bb), None) => Some((bb + 1) as f64),
                (None, Some(ba)) => Some((ba - 1) as f64),
                (None, None) => None,
            });
            let history = &mut self.history[k];
            if mid.is_none() {
                mid = Some(history.last().copied().unwrap_or(FALLBACK[k]));
            }
            let mid = mid.unwrap();
            history.push(mid);
            if history.len() > 100 {
                history.remove(0);
            }
            let alpha = ALPHA[k];
            let mut ema = history[0];
            for &p in &history[1..] {
                ema = alpha * p + (1.0 - alpha) * ema;
            }
            let vol = if history.len() > 1 { py::np_std(history) } else { 1.0 };
            let pos = id.map_or(0, |p| positions[p]);
            let skew = pos as f64 * (mid * 0.001);
            let effective_fair = ema - skew;
            let spread = py::max(2.0, vol * VOL_MULT[k]);
            let bid_price = py::round(effective_fair - spread / 2.0);
            let ask_price = py::round(effective_fair + spread / 2.0);
            let (max_buy, max_sell) = (50 - pos, 50 + pos);
            let (buy_qty, sell_qty) = if pos > 0 {
                (0, max_sell.min(10))
            } else if pos < 0 {
                (max_buy.min(10), 0)
            } else {
                (max_buy.min(5), max_sell.min(5))
            };
            // An order for a product the day doesn't have goes to the engine, which records an error.
            let product = id.unwrap_or(self.products + k);
            if buy_qty > 0 {
                order(out, product, bid_price, buy_qty);
            }
            if sell_qty > 0 {
                order(out, product, ask_price, -sell_qty);
            }
        }
    }
}
