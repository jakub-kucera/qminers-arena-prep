//! bots/rivals/ in Rust: the sniper, the spoofer and the trapper (sniper.py, spoofer.py,
//! trapper.py). Keep each equal to its Python file: tests/test_rust.py checks that both trade the
//! same, and rust/twins.json holds the hash each port was last checked against. Their constants
//! (LIMITS, DEFAULT_LIMIT, EDGE, SPOOF, OFFSET, PERIOD, BAIT, COOLDOWN) come from the Python file's
//! globals, so `--set` reaches them.

use crate::engine::{Bot, TickView};
use crate::json::Value;
use crate::model::{Action, Book, Day, Fill, MarketTrade, OpenOrder, Order, Price};

fn int(globals: &Value, key: &str) -> Result<i64, String> {
    globals.get(key).and_then(Value::as_i64).ok_or_else(|| format!("{key} must be an integer"))
}

/// LIMITS.get(product, DEFAULT_LIMIT), per product of the day.
struct Limits {
    table: Vec<(String, i64)>,
    default: i64,
    by_product: Vec<i64>,
}

impl Limits {
    fn read(globals: &Value) -> Result<Limits, String> {
        let table = globals
            .get("LIMITS")
            .and_then(Value::as_object)
            .ok_or("LIMITS must be a dict")?
            .iter()
            .map(|(k, v)| v.as_i64().map(|v| (k.clone(), v)).ok_or_else(|| format!("LIMITS[{k}] must be an integer")))
            .collect::<Result<_, _>>()?;
        Ok(Limits { table, default: int(globals, "DEFAULT_LIMIT")?, by_product: Vec::new() })
    }

    fn begin_day(&mut self, day: &Day) {
        self.by_product = day.products.iter().map(|p| self.table.iter().rev().find(|(k, _)| k == p).map_or(self.default, |(_, v)| *v)).collect();
    }
}

fn cancels(product: usize, open_orders: &[OpenOrder], out: &mut Vec<Action>) {
    out.extend(open_orders.iter().filter(|o| o.product == product).map(|o| Action::Cancel(o.id)));
}

fn ioc(product: usize, price: Price, quantity: i64) -> Action {
    Action::Order(Order { product, price, quantity, ioc: true })
}

fn rest(product: usize, price: Price, quantity: i64) -> Action {
    Action::Order(Order { product, price, quantity, ioc: false })
}

/// The mid of the outermost levels: the market maker's walls.
fn outer_fair(book: &Book) -> f64 {
    (book.bids[book.bids.len() - 1].0 + book.asks[book.asks.len() - 1].0) as f64 / 2.0
}

/// Takes every order through fair, and cuts inventory at fair (the spoofer's and trapper's step).
fn take_through(product: usize, book: &Book, fair: f64, position: i64, buy_room: &mut i64, sell_room: &mut i64, out: &mut Vec<Action>) {
    for &(price, volume) in &book.bids {
        let p = price as f64;
        if *sell_room <= 0 || !(p > fair || (p >= fair && position > 0)) {
            break;
        }
        let q = volume.min(*sell_room);
        out.push(ioc(product, price, -q));
        *sell_room -= q;
    }
    for &(price, volume) in &book.asks {
        let p = price as f64;
        if *buy_room <= 0 || !(p < fair || (p <= fair && position < 0)) {
            break;
        }
        let q = volume.min(*buy_room);
        out.push(ioc(product, price, q));
        *buy_room -= q;
    }
}

// ---------------------------------------------------------------------------- sniper

pub struct Sniper {
    limits: Limits,
    edge: f64,
}

impl Sniper {
    pub fn from_globals(globals: &Value) -> Result<Sniper, String> {
        let edge = globals.get("EDGE").and_then(Value::as_f64).ok_or("EDGE must be a number")?;
        Ok(Sniper { limits: Limits::read(globals)?, edge })
    }
}

impl Bot for Sniper {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let limit = self.limits.by_product[product];
            cancels(product, open_orders, out);
            let book = tick.books[product].as_ref().unwrap();
            if book.bids.is_empty() || book.asks.is_empty() {
                continue;
            }
            let fair = outer_fair(book);
            let position = positions[product];
            let (mut buy_room, mut sell_room) = (limit - position, limit + position);
            for &(price, volume) in &book.bids {
                let p = price as f64;
                if sell_room <= 0 || !(p >= fair + self.edge || (p >= fair && position > 0)) {
                    break;
                }
                let q = volume.min(if p >= fair + self.edge { sell_room } else { sell_room.min(position) });
                out.push(ioc(product, price, -q));
                sell_room -= q;
            }
            for &(price, volume) in &book.asks {
                let p = price as f64;
                if buy_room <= 0 || !(p <= fair - self.edge || (p <= fair && position < 0)) {
                    break;
                }
                let q = volume.min(if p <= fair - self.edge { buy_room } else { buy_room.min(-position) });
                out.push(ioc(product, price, q));
                buy_room -= q;
            }
        }
    }
}

// ---------------------------------------------------------------------------- spoofer

pub struct Spoofer {
    limits: Limits,
    spoof: i64,
    offset: i64,
    period: i64,
    tick: i64,
}

impl Spoofer {
    pub fn from_globals(globals: &Value) -> Result<Spoofer, String> {
        Ok(Spoofer { limits: Limits::read(globals)?, spoof: int(globals, "SPOOF")?, offset: int(globals, "OFFSET")?, period: int(globals, "PERIOD")?, tick: 0 })
    }
}

impl Bot for Spoofer {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
        self.tick = 0;
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let limit = self.limits.by_product[product];
            cancels(product, open_orders, out);
            let book = tick.books[product].as_ref().unwrap();
            if book.bids.is_empty() || book.asks.is_empty() {
                continue;
            }
            let fair = outer_fair(book);
            let position = positions[product];
            let (mut buy_room, mut sell_room) = (limit - position, limit + position);
            let bid_side = self.tick.div_euclid(self.period).rem_euclid(2) == 0;
            take_through(product, book, fair, position, &mut buy_room, &mut sell_room, out);
            if bid_side && buy_room > 0 {
                out.push(rest(product, book.bids[0].0 - self.offset, self.spoof.min(buy_room)));
            } else if !bid_side && sell_room > 0 {
                out.push(rest(product, book.asks[0].0 + self.offset, -self.spoof.min(sell_room)));
            }
        }
        self.tick += 1;
    }
}

// ---------------------------------------------------------------------------- trapper

pub struct Trapper {
    limits: Limits,
    bait_size: i64,
    period: i64,
    cooldown_ticks: i64,
    tick: i64,
    bait: Vec<Option<(bool, Price)>>, // per product: last tick's bait (bid side?, price)
    cooldown: Vec<i64>,
}

impl Trapper {
    pub fn from_globals(globals: &Value) -> Result<Trapper, String> {
        Ok(Trapper {
            limits: Limits::read(globals)?,
            bait_size: int(globals, "BAIT")?,
            period: int(globals, "PERIOD")?,
            cooldown_ticks: int(globals, "COOLDOWN")?,
            tick: 0,
            bait: Vec::new(),
            cooldown: Vec::new(),
        })
    }
}

impl Bot for Trapper {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.limits.begin_day(day);
        self.tick = 0;
        self.bait = vec![None; day.products.len()];
        self.cooldown = vec![0; day.products.len()];
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        for &product in tick.order {
            let limit = self.limits.by_product[product];
            cancels(product, open_orders, out);
            let book = tick.books[product].as_ref().unwrap();
            if book.bids.is_empty() || book.asks.is_empty() {
                continue;
            }
            let fair = outer_fair(book);
            let position = positions[product];
            let (mut buy_room, mut sell_room) = (limit - position, limit + position);
            let mut bid_side = self.tick.div_euclid(self.period).rem_euclid(2) == 0;
            if position > limit.div_euclid(2) {
                bid_side = false;
            } else if position < (-limit).div_euclid(2) {
                bid_side = true;
            }

            // Spring: someone stepped in front of last tick's bait.
            let mut sprung = false;
            if let Some((bid, price)) = self.bait[product] {
                if bid && book.bids[0].0 == price + 1 && sell_room > 0 {
                    let q = book.bids[0].1.min(sell_room);
                    out.push(ioc(product, book.bids[0].0, -q));
                    sell_room -= q;
                    sprung = true;
                } else if !bid && book.asks[0].0 == price - 1 && buy_room > 0 {
                    let q = book.asks[0].1.min(buy_room);
                    out.push(ioc(product, book.asks[0].0, q));
                    buy_room -= q;
                    sprung = true;
                }
            }
            if sprung {
                self.cooldown[product] = self.cooldown_ticks;
            }

            take_through(product, book, fair, position, &mut buy_room, &mut sell_room, out);

            let mut bait = None;
            if self.cooldown[product] > 0 {
                self.cooldown[product] -= 1;
            } else if bid_side && buy_room > 0 {
                let price = (book.bids[0].0 + 1).min((fair - 0.5).floor() as i64);
                if price < book.asks[0].0 {
                    out.push(rest(product, price, self.bait_size.min(buy_room)));
                    bait = Some((true, price));
                }
            } else if !bid_side && sell_room > 0 {
                let price = (book.asks[0].0 - 1).max((fair + 0.5).ceil() as i64);
                if price > book.bids[0].0 {
                    out.push(rest(product, price, -self.bait_size.min(sell_room)));
                    bait = Some((false, price));
                }
            }
            self.bait[product] = bait;
        }
        self.tick += 1;
    }
}
