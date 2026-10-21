//! bots/zoo/chatgpt/gpt-5-6-luna_market_maker.py

use super::{best_ask, best_bid, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];
const LIMITS: [i64; 3] = [50, 50, 50];
const ALPHA: [f64; 3] = [f64::NAN, 0.20, 0.12];
const QUOTE_HALF_SPREAD: [i64; 3] = [2, 1, 2];
const TAKE_EDGE: [i64; 3] = [1, 1, 2];
const QUOTE_SIZE: [i64; 3] = [10, 10, 8];
const STRENGTH: [f64; 3] = [2.0, 1.5, 2.0];

/// memory["products"][product]: its "ema" and "previous_ema" ("mid" is never read).
#[derive(Clone, Copy)]
struct Seen {
    ema: f64,
    previous_ema: f64,
}

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    seen: Vec<Option<Seen>>,
}

impl Bot {
    fn fair_value(&mut self, product: usize, k: usize, mid: f64) -> f64 {
        if k == 0 {
            return 10000.0;
        }
        let previous = self.seen[product];
        let ema = previous.map_or(mid, |p| p.ema);
        let previous_ema = previous.map_or(ema, |p| p.previous_ema);
        let alpha = ALPHA[k];
        let ema = alpha * mid + (1.0 - alpha) * ema;
        self.seen[product] = Some(Seen { ema, previous_ema: previous.map_or(ema, |p| p.ema) });
        let momentum = ema - previous_ema;
        if k == 1 {
            ema + 0.25 * momentum
        } else {
            ema + 0.35 * momentum
        }
    }
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.seen = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let Some(k) = self.which[product] else { continue };
            let book = tick.books[product].as_ref().unwrap();
            let (Some(bb), Some(ba)) = (best_bid(book), best_ask(book)) else { continue };
            let mid = (bb + ba) as f64 / 2.0;
            let fair = self.fair_value(product, k, mid);
            let position = positions[product];
            let (limit, edge) = (LIMITS[k], TAKE_EDGE[k] as f64);
            let (mut buy_used, mut sell_used) = (0, 0);
            let mut asks = book.asks.clone();
            asks.sort_by_key(|l| l.0);
            for (price, volume) in asks {
                if volume <= 0 || price as f64 > fair - edge {
                    break;
                }
                let quantity = volume.min(limit - position - buy_used);
                if quantity > 0 {
                    order(out, product, price, quantity);
                    buy_used += quantity;
                }
            }
            let mut bids = book.bids.clone();
            bids.sort_by(|a, b| b.0.cmp(&a.0));
            for (price, volume) in bids {
                if volume <= 0 || (price as f64) < fair + edge {
                    break;
                }
                let quantity = volume.min(limit + position - sell_used);
                if quantity > 0 {
                    order(out, product, price, -quantity);
                    sell_used += quantity;
                }
            }
            let inventory_skew = STRENGTH[k] * position as f64 / limit as f64;
            let quote_fair = fair - inventory_skew;
            let half_spread = QUOTE_HALF_SPREAD[k] as f64;
            let desired_bid = ((quote_fair - half_spread).floor() as i64).min(ba - 1);
            let desired_ask = ((quote_fair + half_spread).ceil() as i64).max(bb + 1);
            let size = QUOTE_SIZE[k];
            let buy_room = limit - position - buy_used;
            let sell_room = limit + position - sell_used;
            if buy_room > 0 {
                order(out, product, desired_bid, size.min(buy_room));
            }
            if sell_room > 0 {
                order(out, product, desired_ask, -size.min(sell_room));
            }
        }
    }
}
