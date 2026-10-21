//! bots/zoo/chatgpt/gpt-5-6-luna_baseline.py

use super::py;
use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const LIMITS: [i64; 3] = [50, 50, 50];
const DEFAULT_LIMIT: i64 = 50;
const RESIN_FAIR: i64 = 10000;

/// history[symbol]: None where Python's key is absent.
#[derive(Clone, Copy, Default)]
struct History {
    mid: Option<f64>,
    ema_fast: Option<f64>,
    ema_slow: Option<f64>,
    velocity: Option<f64>,
    volatility: Option<f64>,
}

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    history: Vec<History>,
}

fn ema(old: Option<f64>, value: f64, alpha: f64) -> f64 {
    match old {
        None => value,
        Some(old) => alpha * value + (1.0 - alpha) * old,
    }
}

/// _book_statistics: best bid, best ask, and the micro-price (or the one side's price).
fn book_statistics(book: &Book) -> (Option<i64>, Option<i64>, Option<f64>) {
    let (bb, ba) = (best_bid(book), best_ask(book));
    match (bb, ba) {
        (Some(b), Some(a)) => {
            let bid_volume = book.bids.iter().find(|l| l.0 == b).unwrap().1.max(1);
            let ask_volume = book.asks.iter().find(|l| l.0 == a).unwrap().1.max(1);
            (bb, ba, Some((b * ask_volume + a * bid_volume) as f64 / (bid_volume + ask_volume) as f64))
        }
        (Some(b), None) => (bb, None, Some(b as f64)),
        (None, Some(a)) => (None, ba, Some(a as f64)),
        (None, None) => (None, None, None),
    }
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.history = vec![History::default(); day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &symbol in tick.order {
            let k = self.which[symbol];
            let limit = k.map_or(DEFAULT_LIMIT, |k| LIMITS[k]);
            let position = positions[symbol];
            let book = tick.books[symbol].as_ref().unwrap();
            let (best_bid, best_ask, observed) = book_statistics(book);
            let Some(observed) = observed else { continue };
            let h = &mut self.history[symbol];
            let previous_price = h.mid.unwrap_or(observed);
            h.mid = Some(observed);
            h.ema_fast = Some(ema(h.ema_fast, observed, 0.22));
            h.ema_slow = Some(ema(h.ema_slow, observed, 0.035));
            h.velocity = Some(ema(h.velocity, observed - previous_price, 0.20));
            h.volatility = Some(ema(h.volatility, (observed - previous_price).abs(), 0.08));
            let (fast, slow, velocity, volatility) = (h.ema_fast.unwrap(), h.ema_slow.unwrap(), h.velocity.unwrap(), h.volatility.unwrap());
            let (fair_value, quote_edge, take_edge) = match k {
                Some(0) => (RESIN_FAIR as f64, 1.0, 0.0),
                Some(1) => (0.65 * fast + 0.35 * slow, py::max(1.0, py::min(3.0, 1.1 + 0.7 * volatility)), 0.5),
                _ => {
                    let momentum_value = fast + py::max(-3.0, py::min(3.0, 1.8 * velocity));
                    (0.72 * momentum_value + 0.28 * slow, py::max(1.0, py::min(5.0, 1.4 + 0.9 * volatility)), 0.7)
                }
            };
            let mut buy_room = (limit - position).max(0);
            let mut sell_room = (limit + position).max(0);
            if let Some(a) = best_ask {
                if a as f64 <= fair_value - take_edge && buy_room > 0 {
                    let quantity = buy_room.min(book.asks.iter().find(|l| l.0 == a).unwrap().1);
                    if quantity > 0 {
                        order(out, symbol, a, quantity);
                        buy_room -= quantity;
                    }
                }
            }
            if let Some(b) = best_bid {
                if b as f64 >= fair_value + take_edge && sell_room > 0 {
                    let quantity = sell_room.min(book.bids.iter().find(|l| l.0 == b).unwrap().1);
                    if quantity > 0 {
                        order(out, symbol, b, -quantity);
                        sell_room -= quantity;
                    }
                }
            }
            let inventory_bias = position as f64 / limit as f64;
            let mut buy_quote = (fair_value - quote_edge - 1.2 * inventory_bias).trunc() as i64;
            let mut sell_quote = (fair_value + quote_edge - 1.2 * inventory_bias).trunc() as i64;
            if let Some(b) = best_bid {
                buy_quote = buy_quote.min(b + 1);
            }
            if let Some(a) = best_ask {
                sell_quote = sell_quote.max(a - 1);
            }
            if buy_quote >= sell_quote {
                buy_quote = (fair_value - quote_edge).trunc() as i64;
                sell_quote = (fair_value + quote_edge).trunc() as i64;
            }
            let quote_size = if k == Some(0) { 8 } else { 6 };
            if buy_room > 0 && best_ask.is_none_or(|a| buy_quote < a) {
                order(out, symbol, buy_quote, buy_room.min(quote_size));
            }
            if sell_room > 0 && best_bid.is_none_or(|b| sell_quote > b) {
                order(out, symbol, sell_quote, -sell_room.min(quote_size));
            }
        }
    }
}
