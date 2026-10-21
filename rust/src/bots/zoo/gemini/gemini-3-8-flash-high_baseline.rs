//! python/bots/zoo/gemini/gemini-3-8-flash-high_baseline.py

use super::{lookup, order};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder, Price};

const PRODUCTS: [&str; 3] = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"];

/// OrderManager: buys and sells summed per price (in first-seen order) within the budgets.
struct OrderManager {
    current_pos: i64,
    buy_budget: i64,
    sell_budget: i64,
    buy_orders: Vec<(Price, i64)>,
    sell_orders: Vec<(Price, i64)>,
    total_bought: i64,
    total_sold: i64,
}

impl OrderManager {
    fn new(limit: i64, current_pos: i64) -> Self {
        OrderManager {
            current_pos,
            buy_budget: (limit - current_pos).max(0),
            sell_budget: (limit + current_pos).max(0),
            buy_orders: Vec::new(),
            sell_orders: Vec::new(),
            total_bought: 0,
            total_sold: 0,
        }
    }

    fn add(orders: &mut Vec<(Price, i64)>, price: Price, quantity: i64) {
        match orders.iter_mut().find(|(p, _)| *p == price) {
            Some((_, q)) => *q += quantity,
            None => orders.push((price, quantity)),
        }
    }

    fn buy(&mut self, price: Price, quantity: i64) -> i64 {
        if quantity <= 0 {
            return 0;
        }
        let fill = quantity.min(self.buy_budget);
        if fill > 0 {
            Self::add(&mut self.buy_orders, price, fill);
            self.buy_budget -= fill;
            self.total_bought += fill;
            return fill;
        }
        0
    }

    fn sell(&mut self, price: Price, quantity: i64) -> i64 {
        if quantity <= 0 {
            return 0;
        }
        let fill = quantity.min(self.sell_budget);
        if fill > 0 {
            Self::add(&mut self.sell_orders, price, fill);
            self.sell_budget -= fill;
            self.total_sold += fill;
            return fill;
        }
        0
    }

    fn effective_pos(&self) -> i64 {
        self.current_pos + self.total_bought - self.total_sold
    }

    fn emit(&self, product: usize, out: &mut Vec<Action>) {
        for &(p, q) in &self.buy_orders {
            if q > 0 {
                order(out, product, p, q);
            }
        }
        for &(p, q) in &self.sell_orders {
            if q > 0 {
                order(out, product, p, -q);
            }
        }
    }
}

#[derive(Default)]
pub struct Bot {
    which: Vec<Option<usize>>,
    kelp_ema: Option<f64>,
    squid_fast: Option<f64>,
    squid_slow: Option<f64>,
    squid_mids: Vec<f64>,
}

fn sorted(book: &Book) -> (Vec<(Price, i64)>, Vec<(Price, i64)>) {
    let mut asks = book.asks.clone();
    asks.sort_by_key(|l| l.0);
    let mut bids = book.bids.clone();
    bids.sort_by(|a, b| b.0.cmp(&a.0));
    (asks, bids)
}

fn trade_rainforest_resin(product: usize, book: &Book, pos: i64, out: &mut Vec<Action>) {
    let mut om = OrderManager::new(50, pos);
    let (asks, bids) = sorted(book);
    for &(ask_p, avail) in &asks {
        if ask_p <= 9998 {
            om.buy(ask_p, avail);
        } else if ask_p == 9999 && om.effective_pos() < 0 {
            let q = avail.min(-om.effective_pos());
            om.buy(ask_p, q);
        }
    }
    for &(bid_p, avail) in &bids {
        if bid_p >= 10002 {
            om.sell(bid_p, avail);
        } else if bid_p == 10001 && om.effective_pos() > 0 {
            let q = avail.min(om.effective_pos());
            om.sell(bid_p, q);
        }
    }
    let eff_pos = om.effective_pos();
    if om.buy_budget > 0 {
        let bid_p = if eff_pos < -15 {
            Some(9999)
        } else if eff_pos < 25 {
            Some(9998)
        } else if eff_pos < 45 {
            Some(9997)
        } else {
            None
        };
        if let Some(p) = bid_p {
            let q = om.buy_budget;
            om.buy(p, q);
        }
    }
    if om.sell_budget > 0 {
        let ask_p = if eff_pos > 15 {
            Some(10001)
        } else if eff_pos > -25 {
            Some(10002)
        } else if eff_pos > -45 {
            Some(10003)
        } else {
            None
        };
        if let Some(p) = ask_p {
            let q = om.sell_budget;
            om.sell(p, q);
        }
    }
    om.emit(product, out);
}

impl Bot {
    fn trade_kelp(&mut self, product: usize, book: &Book, pos: i64, out: &mut Vec<Action>) {
        let mut om = OrderManager::new(50, pos);
        let (asks, bids) = sorted(book);
        if asks.is_empty() && bids.is_empty() {
            return;
        }
        let (best_ask, ask_vol) = asks.first().copied().unwrap_or((2032, 1));
        let (best_bid, bid_vol) = bids.first().copied().unwrap_or((2028, 1));
        let mid = (best_bid + best_ask) as f64 / 2.0;
        let micro = (best_bid * ask_vol + best_ask * bid_vol) as f64 / (bid_vol + ask_vol) as f64;
        let ema = 0.3 * micro + 0.7 * self.kelp_ema.unwrap_or(mid);
        self.kelp_ema = Some(ema);
        let fair_value = 0.6 * micro + 0.4 * ema;
        for &(ask_p, avail) in &asks {
            let p = ask_p as f64;
            if p <= fair_value - 1.0 {
                om.buy(ask_p, avail);
            } else if p < fair_value - 0.2 && om.effective_pos() < 0 {
                let q = avail.min(-om.effective_pos());
                om.buy(ask_p, q);
            }
        }
        for &(bid_p, avail) in &bids {
            let p = bid_p as f64;
            if p >= fair_value + 1.0 {
                om.sell(bid_p, avail);
            } else if p > fair_value + 0.2 && om.effective_pos() > 0 {
                let q = avail.min(om.effective_pos());
                om.sell(bid_p, q);
            }
        }
        let eff_pos = om.effective_pos();
        let inv_skew = 1.5 * (eff_pos as f64 / 50.0);
        let res_price = fair_value - inv_skew;
        if om.buy_budget > 0 {
            let target_bid = (res_price - 0.5).trunc() as i64;
            let mut my_bid = if best_ask - best_bid >= 2 {
                let penny_bid = best_bid + 1;
                if penny_bid <= target_bid { penny_bid } else { best_bid.min(target_bid) }
            } else {
                best_bid.min(target_bid)
            };
            my_bid = my_bid.min(best_ask - 1);
            if my_bid > 0 {
                let q = om.buy_budget;
                om.buy(my_bid, q);
            }
        }
        if om.sell_budget > 0 {
            let mut target_ask = (res_price + 0.5).trunc() as i64;
            if target_ask as f64 <= res_price {
                target_ask += 1;
            }
            let mut my_ask = if best_ask - best_bid >= 2 {
                let penny_ask = best_ask - 1;
                if penny_ask >= target_ask { penny_ask } else { best_ask.max(target_ask) }
            } else {
                best_ask.max(target_ask)
            };
            my_ask = my_ask.max(best_bid + 1);
            if my_ask > 0 {
                let q = om.sell_budget;
                om.sell(my_ask, q);
            }
        }
        om.emit(product, out);
    }

    fn trade_squid_ink(&mut self, product: usize, book: &Book, pos: i64, out: &mut Vec<Action>) {
        let mut om = OrderManager::new(50, pos);
        let (asks, bids) = sorted(book);
        if asks.is_empty() && bids.is_empty() {
            return;
        }
        let (best_ask, ask_vol) = asks.first().copied().unwrap_or((1971, 1));
        let (best_bid, bid_vol) = bids.first().copied().unwrap_or((1968, 1));
        let mid = (best_bid + best_ask) as f64 / 2.0;
        let tot_bid: i64 = book.bids.iter().map(|l| l.1).sum();
        let tot_ask: i64 = book.asks.iter().map(|l| l.1).sum();
        let obi = if tot_bid + tot_ask > 0 { (tot_bid - tot_ask) as f64 / (tot_bid + tot_ask) as f64 } else { 0.0 };
        let _ = (ask_vol, bid_vol); // the micro-price is computed in Python but never used
        let ema_fast = 0.333 * mid + 0.667 * self.squid_fast.unwrap_or(mid);
        let ema_slow = 0.095 * mid + 0.905 * self.squid_slow.unwrap_or(mid);
        self.squid_fast = Some(ema_fast);
        self.squid_slow = Some(ema_slow);
        self.squid_mids.push(mid);
        let short_roc = if self.squid_mids.len() >= 4 { mid - self.squid_mids[self.squid_mids.len() - 3] } else { 0.0 };
        if self.squid_mids.len() > 40 {
            let drop = self.squid_mids.len() - 40;
            self.squid_mids.drain(..drop);
        }
        let signal = (ema_fast - ema_slow) + 0.6 * short_roc + 0.6 * obi;
        let target_pos = if signal > 2.0 {
            45
        } else if signal > 0.8 {
            28
        } else if signal > 0.2 {
            12
        } else if signal < -2.0 {
            -45
        } else if signal < -0.8 {
            -28
        } else if signal < -0.2 {
            -12
        } else {
            0
        };
        let eff_pos = om.effective_pos();
        if eff_pos < target_pos {
            let mut needed = target_pos - eff_pos;
            for &(ask_p, avail) in &asks {
                if needed <= 0 || (signal <= 1.2 && ask_p as f64 > mid) {
                    break;
                }
                needed -= om.buy(ask_p, avail.min(needed));
            }
            if om.buy_budget > 0 {
                let bid_p = if best_ask - best_bid >= 2 { (best_bid + 1).min(best_ask - 1) } else { best_bid };
                let q = om.buy_budget;
                om.buy(bid_p, q);
            }
            if om.sell_budget > 0 && signal < 1.5 {
                let q = om.sell_budget;
                om.sell(best_ask.max(best_bid + 1), q);
            }
        } else if eff_pos > target_pos {
            let mut needed = eff_pos - target_pos;
            for &(bid_p, avail) in &bids {
                if needed <= 0 || (signal >= -1.2 && (bid_p as f64) < mid) {
                    break;
                }
                needed -= om.sell(bid_p, avail.min(needed));
            }
            if om.sell_budget > 0 {
                let ask_p = if best_ask - best_bid >= 2 { (best_ask - 1).max(best_bid + 1) } else { best_ask };
                let q = om.sell_budget;
                om.sell(ask_p, q);
            }
            if om.buy_budget > 0 && signal > -1.5 {
                let q = om.buy_budget;
                om.buy(best_bid.min(best_ask - 1), q);
            }
        } else {
            if om.buy_budget > 0 {
                let bid_p = if best_ask - best_bid >= 2 { best_bid + 1 } else { best_bid };
                let q = om.buy_budget;
                om.buy(bid_p.min(best_ask - 1), q);
            }
            if om.sell_budget > 0 {
                let ask_p = if best_ask - best_bid >= 2 { best_ask - 1 } else { best_ask };
                let q = om.sell_budget;
                om.sell(ask_p.max(best_bid + 1), q);
            }
        }
        om.emit(product, out);
    }
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.which = lookup(day, &PRODUCTS);
        self.kelp_ema = None;
        self.squid_fast = None;
        self.squid_slow = None;
        self.squid_mids.clear();
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let pos = positions[product];
            match self.which[product] {
                Some(0) => trade_rainforest_resin(product, book, pos, out),
                Some(1) => self.trade_kelp(product, book, pos, out),
                Some(2) => self.trade_squid_ink(product, book, pos, out),
                _ => {}
            }
        }
    }
}
