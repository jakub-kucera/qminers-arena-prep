//! python/bots/zoo/claude/opus-5.5_market_maker.py

use super::{asks_asc, ask_wall_high, best_ask, best_bid, bid_wall_low, bids_desc, lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder};

const LIMIT: i64 = 50;
const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

struct P {
    fixed: Option<f64>,
    take_edge: f64,
    disregard: f64,
    join: f64,
    default: f64,
    soft: i64,
    reversion: f64,
    quote_size: i64,
}

const PARAMS: [P; 3] = [
    P { fixed: Some(10000.0), take_edge: 1.0, disregard: 1.0, join: 2.0, default: 4.0, soft: 25, reversion: 0.0, quote_size: 50 },
    P { fixed: None, take_edge: 1.0, disregard: 1.0, join: 0.0, default: 2.0, soft: 25, reversion: 0.0, quote_size: 50 },
    P { fixed: None, take_edge: 1.0, disregard: 1.0, join: 0.0, default: 2.0, soft: 15, reversion: 0.15, quote_size: 20 },
];

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    last_wm: Vec<Option<f64>>, // memory["wm"]
}

fn wall_mid(book: &Book) -> Option<f64> {
    if book.bids.is_empty() || book.asks.is_empty() {
        return None;
    }
    let (bid, ask) = (bid_wall_low(book), ask_wall_high(book));
    if bid >= ask {
        return Some((best_bid(book).unwrap() + best_ask(book).unwrap()) as f64 / 2.0);
    }
    Some((bid + ask) as f64 / 2.0)
}

impl Bot {
    fn trade(&mut self, product: usize, p: &P, book: &Book, position: i64, out: &mut Vec<Action>) {
        let fair = match p.fixed {
            Some(fixed) => fixed,
            None => {
                let prev = self.last_wm[product];
                let (wm, fair) = match wall_mid(book) {
                    None => match prev {
                        None => return,
                        Some(prev) => (prev, prev),
                    },
                    Some(wm) => match prev {
                        Some(prev) if p.reversion != 0.0 => (wm, wm - p.reversion * (wm - prev)),
                        _ => (wm, wm),
                    },
                };
                self.last_wm[product] = Some(wm);
                fair
            }
        };
        let (mut buy_room, mut sell_room, mut pos) = (LIMIT - position, LIMIT + position, position);
        for &(price, vol) in &asks_asc(book) {
            if buy_room <= 0 {
                break;
            }
            let pr = price as f64;
            if pr <= fair - p.take_edge || (pr <= fair && pos < 0) {
                let mut q = vol.min(buy_room);
                if pr >= fair {
                    q = q.min(-pos);
                }
                if q > 0 {
                    order(out, product, price, q);
                    buy_room -= q;
                    pos += q;
                }
            } else {
                break;
            }
        }
        for &(price, vol) in &bids_desc(book) {
            if sell_room <= 0 {
                break;
            }
            let pr = price as f64;
            if pr >= fair + p.take_edge || (pr >= fair && pos > 0) {
                let mut q = vol.min(sell_room);
                if pr <= fair {
                    q = q.min(pos);
                }
                if q > 0 {
                    order(out, product, price, -q);
                    sell_room -= q;
                    pos -= q;
                }
            } else {
                break;
            }
        }
        let asks_out = book.asks.iter().map(|l| l.0).filter(|&pr| pr as f64 > fair + p.disregard).min();
        let bids_out = book.bids.iter().map(|l| l.0).filter(|&pr| (pr as f64) < fair - p.disregard).max();
        let mut ask = match asks_out {
            Some(best) => if best as f64 - fair <= p.join { best } else { best - 1 },
            None => (fair + p.default).ceil() as i64,
        };
        let mut bid = match bids_out {
            Some(best) => if fair - best as f64 <= p.join { best } else { best + 1 },
            None => (fair - p.default).floor() as i64,
        };
        let mut min_ask = fair.floor() as i64 + 1;
        let mut max_bid = fair.ceil() as i64 - 1;
        if pos > p.soft {
            ask -= 1;
            bid -= 1;
            min_ask = fair.ceil() as i64;
        } else if pos < -p.soft {
            ask += 1;
            bid += 1;
            max_bid = fair.floor() as i64;
        }
        ask = ask.max(min_ask);
        bid = bid.min(max_bid);
        if bid >= ask {
            bid = ask - 1;
        }
        let (bq, sq) = (buy_room.min(p.quote_size), sell_room.min(p.quote_size));
        if bq > 0 {
            order(out, product, bid, bq);
        }
        if sq > 0 {
            order(out, product, ask, -sq);
        }
    }
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.last_wm = vec![None; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let Some(k) = self.which[product] else { continue };
            self.trade(product, &PARAMS[k], tick.books[product].as_ref().unwrap(), positions[product], out);
        }
    }
}
