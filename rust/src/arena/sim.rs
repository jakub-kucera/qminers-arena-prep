//! arena/sim.py's agent-based market, ported function for function (the Python names are kept, so
//! each piece can be read next to its original; the rules are in that module's docstring). Every
//! agent draws from its own `random.Random`, seeded and drawn exactly as in Python, so a seed gives
//! the same day to the bit: the same books, trades and fundamental, and with bots in it the same
//! fills, orders, cancels, breaches, races and errors.
//!
//! The spec comes from Python (`dataclasses.asdict` of a MarketSpec, written by arena/rust.py), so
//! presets, `--spec` overrides and regimes stay in Python. Prices are whole ticks, as in Python.

use std::collections::{BTreeMap, HashMap};

use crate::arena::engine::{breaches, known, new_result, Bot, DayResult, TickView};
use crate::support::json::Value;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, Name, OpenOrder, Order, Source, Tick};
use crate::support::py::{self, Num};
use crate::support::pyrandom::PyRandom;

pub const DEPTH: usize = 3; // levels a side in a snapshot, as in Prosperity's price files

extern "C" {
    fn exp(x: f64) -> f64;
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Maker,
    Limit,
    Noise,
    Value,
    Momentum,
}

pub const AGENTS: [Kind; 5] = [Kind::Maker, Kind::Limit, Kind::Noise, Kind::Value, Kind::Momentum];

impl Kind {
    pub fn name(self) -> &'static str {
        match self {
            Kind::Maker => "maker",
            Kind::Limit => "limit",
            Kind::Noise => "noise",
            Kind::Value => "value",
            Kind::Momentum => "momentum",
        }
    }
}

// ---------------------------------------------------------------------------- specs

#[derive(Clone, Debug)]
pub struct Fundamental {
    pub start: f64,
    pub level: Option<f64>,
    pub reversion: f64,
    pub sd: f64,
    pub drift: f64,
    pub jump_rate: f64,
    pub jump_size: f64,
    pub snap_back: Option<i64>,
    pub jump_excite: f64,
    pub jump_decay: f64,
    pub jump_reverse: Option<f64>,
    pub regime_at: Option<f64>,
    pub regime_shift: f64,
    pub regime_drift: f64,
}

#[derive(Clone, Debug)]
pub struct Maker {
    pub half_spread: f64,
    pub size: (i64, i64),
    pub noise: f64,
    pub skew: f64,
    pub refresh: f64,
    pub first: bool,
}

#[derive(Clone, Debug)]
pub struct LimitTraders {
    pub rate: f64,
    pub offset: (f64, f64),
    pub size: (i64, i64),
    pub noise: f64,
    pub life: i64,
}

#[derive(Clone, Debug)]
pub struct NoiseTakers {
    pub rate: f64,
    pub size: (i64, i64),
    pub buy_share: f64,
    pub sell_size: Option<(i64, i64)>,
    pub persistence: f64,
}

#[derive(Clone, Debug)]
pub struct ValueTakers {
    pub rate: f64,
    pub size: (i64, i64),
    pub noise: f64,
    pub threshold: f64,
}

#[derive(Clone, Debug)]
pub struct MomentumTakers {
    pub rate: f64,
    pub size: (i64, i64),
    pub short: usize,
    pub long: usize,
    pub threshold: f64,
}

#[derive(Clone, Debug)]
pub struct ProductSpec {
    pub name: String,
    pub limit: i64,
    pub fundamental: Fundamental,
    pub maker: Maker,
    pub limit_traders: LimitTraders,
    pub noise: NoiseTakers,
    pub value: ValueTakers,
    pub momentum: MomentumTakers,
}

#[derive(Clone, Debug)]
pub struct MarketSpec {
    pub products: Vec<ProductSpec>,
    pub ticks: usize,
    pub step: i64,
    pub names: bool,
}

/// Reads one dataclass's fields from `dataclasses.asdict`'s output, naming the field that is off.
struct Fields<'a> {
    value: &'a Value,
    path: String,
}

impl<'a> Fields<'a> {
    fn of(value: &'a Value, path: &str) -> Result<Self, String> {
        value.as_object().ok_or_else(|| format!("{path} must be an object"))?;
        Ok(Fields { value, path: path.to_string() })
    }

    fn get(&self, key: &str) -> Result<&'a Value, String> {
        self.value.get(key).ok_or_else(|| format!("{}.{key} is missing", self.path))
    }

    fn sub(&self, key: &str) -> Result<Fields<'a>, String> {
        Fields::of(self.get(key)?, &format!("{}.{key}", self.path))
    }

    fn float(&self, key: &str) -> Result<f64, String> {
        match self.get(key)? {
            Value::Int(v) => Ok(*v as f64),
            Value::Float(v) => Ok(*v),
            _ => Err(format!("{}.{key} must be a number", self.path)),
        }
    }

    fn opt_float(&self, key: &str) -> Result<Option<f64>, String> {
        if self.get(key)?.is_null() { Ok(None) } else { self.float(key).map(Some) }
    }

    fn int(&self, key: &str) -> Result<i64, String> {
        match self.get(key)? {
            Value::Int(v) => Ok(*v),
            _ => Err(format!("{}.{key} must be an integer", self.path)),
        }
    }

    fn opt_int(&self, key: &str) -> Result<Option<i64>, String> {
        if self.get(key)?.is_null() { Ok(None) } else { self.int(key).map(Some) }
    }

    fn bool(&self, key: &str) -> Result<bool, String> {
        match self.get(key)? {
            Value::Bool(v) => Ok(*v),
            _ => Err(format!("{}.{key} must be true or false", self.path)),
        }
    }

    /// A (low, high) pair of ints, as randint takes them.
    fn ints(&self, key: &str) -> Result<(i64, i64), String> {
        match self.get(key)?.as_list() {
            Some([Value::Int(a), Value::Int(b)]) if a <= b => Ok((*a, *b)),
            _ => Err(format!("{}.{key} must be a pair of integers, low first", self.path)),
        }
    }

    fn opt_ints(&self, key: &str) -> Result<Option<(i64, i64)>, String> {
        if self.get(key)?.is_null() { Ok(None) } else { self.ints(key).map(Some) }
    }

    fn floats(&self, key: &str) -> Result<(f64, f64), String> {
        match self.get(key)?.as_list() {
            Some([a, b]) => match (a.as_f64(), b.as_f64()) {
                (Some(a), Some(b)) => Ok((a, b)),
                _ => Err(format!("{}.{key} must be a pair of numbers", self.path)),
            },
            _ => Err(format!("{}.{key} must be a pair of numbers", self.path)),
        }
    }
}

impl MarketSpec {
    /// From `dataclasses.asdict(spec)` as JSON.
    pub fn from_json(value: &Value) -> Result<MarketSpec, String> {
        let m = Fields::of(value, "spec")?;
        let products = m.get("products")?.as_list().ok_or("spec.products must be a list")?;
        let mut out = Vec::new();
        for (k, p) in products.iter().enumerate() {
            let p = Fields::of(p, &format!("spec.products[{k}]"))?;
            let name = p.get("name")?.as_str().ok_or("a product's name must be a string")?.to_string();
            let p = Fields { path: name.clone(), ..p };
            let (f, mk, lt, nt, vt, mt) = (p.sub("fundamental")?, p.sub("maker")?, p.sub("limit_traders")?, p.sub("noise")?, p.sub("value")?, p.sub("momentum")?);
            let momentum = MomentumTakers {
                rate: mt.float("rate")?,
                size: mt.ints("size")?,
                short: mt.int("short")?.try_into().map_err(|_| format!("{name}.momentum.short must be positive"))?,
                long: mt.int("long")?.try_into().map_err(|_| format!("{name}.momentum.long must be positive"))?,
                threshold: mt.float("threshold")?,
            };
            if momentum.short == 0 || momentum.long == 0 {
                return Err(format!("{name}.momentum: short and long must be positive (Python divides by them)"));
            }
            out.push(ProductSpec {
                limit: p.int("limit")?,
                fundamental: Fundamental {
                    start: f.float("start")?,
                    level: f.opt_float("level")?,
                    reversion: f.float("reversion")?,
                    sd: f.float("sd")?,
                    drift: f.float("drift")?,
                    jump_rate: f.float("jump_rate")?,
                    jump_size: f.float("jump_size")?,
                    snap_back: f.opt_int("snap_back")?,
                    jump_excite: f.float("jump_excite")?,
                    jump_decay: f.float("jump_decay")?,
                    jump_reverse: f.opt_float("jump_reverse")?,
                    regime_at: f.opt_float("regime_at")?,
                    regime_shift: f.float("regime_shift")?,
                    regime_drift: f.float("regime_drift")?,
                },
                maker: Maker {
                    half_spread: mk.float("half_spread")?,
                    size: mk.ints("size")?,
                    noise: mk.float("noise")?,
                    skew: mk.float("skew")?,
                    refresh: mk.float("refresh")?,
                    first: mk.bool("first")?,
                },
                limit_traders: LimitTraders {
                    rate: lt.float("rate")?,
                    offset: lt.floats("offset")?,
                    size: lt.ints("size")?,
                    noise: lt.float("noise")?,
                    life: lt.int("life")?,
                },
                noise: NoiseTakers {
                    rate: nt.float("rate")?,
                    size: nt.ints("size")?,
                    buy_share: nt.float("buy_share")?,
                    sell_size: nt.opt_ints("sell_size")?,
                    persistence: nt.float("persistence")?,
                },
                value: ValueTakers { rate: vt.float("rate")?, size: vt.ints("size")?, noise: vt.float("noise")?, threshold: vt.float("threshold")? },
                momentum,
                name,
            });
        }
        let mut names: Vec<&str> = out.iter().map(|p| p.name.as_str()).collect();
        names.sort_unstable();
        if names.windows(2).any(|w| w[0] == w[1]) {
            return Err("spec.products: each product once".into());
        }
        Ok(MarketSpec {
            products: out,
            ticks: m.int("ticks")?.try_into().map_err(|_| "spec.ticks must not be negative")?,
            step: m.int("step")?,
            names: m.bool("names")?,
        })
    }
}

// ---------------------------------------------------------------------------- the book

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Owner {
    Agent(Kind),
    Bot(usize),
}

#[derive(Clone, Debug)]
struct SimOrder {
    id: u64,
    owner: Owner,
    product: usize, // the product's index in the spec
    price: i64,
    quantity: i64, // left to fill, signed
    timestamp: i64,
    expires: Option<i64>, // tick from which its agent cancels it
    buying: bool,
}

impl SimOrder {
    fn new(id: u64, owner: Owner, product: usize, price: i64, quantity: i64, timestamp: i64, expires: Option<i64>) -> Self {
        SimOrder { id, owner, product, price, quantity, timestamp, expires, buying: quantity > 0 }
    }
}

/// A match: the resting order (its id, owner and what is left of it), the price and the volume.
#[derive(Clone, Copy)]
struct Match {
    id: u64,
    owner: Owner,
    left: i64,
    price: i64,
    volume: i64,
}

/// One product's live limit order book, price-time priority (`_Book`).
#[derive(Default)]
struct SimBook {
    bids: BTreeMap<i64, Vec<SimOrder>>,
    asks: BTreeMap<i64, Vec<SimOrder>>,
    orders: HashMap<u64, (bool, i64)>, // resting orders: id -> (buying, price)
}

impl SimBook {
    fn best_bid(&self) -> Option<i64> {
        self.bids.keys().next_back().copied()
    }

    fn best_ask(&self) -> Option<i64> {
        self.asks.keys().next().copied()
    }

    /// Matches an incoming order best price first, then rests what's left if `rest`; with
    /// `protect` it skips resting orders of its own owner. Pushes each match onto `matches`.
    fn submit(&mut self, order: &mut SimOrder, rest: bool, protect: bool, matches: &mut Vec<Match>) {
        let buying = order.buying;
        let side = if buying { &mut self.asks } else { &mut self.bids };
        let prices: Vec<i64> = if buying { side.keys().copied().collect() } else { side.keys().rev().copied().collect() };
        for price in prices {
            if if buying { price > order.price } else { price < order.price } {
                break;
            }
            let queue = side.get_mut(&price).unwrap();
            for there in queue.iter_mut() {
                if order.quantity == 0 {
                    break;
                }
                if protect && there.owner == order.owner {
                    continue;
                }
                let volume = order.quantity.abs().min(there.quantity.abs());
                there.quantity += if buying { volume } else { -volume };
                order.quantity -= if buying { volume } else { -volume };
                matches.push(Match { id: there.id, owner: there.owner, left: there.quantity, price, volume });
            }
            // _prune
            let orders = &mut self.orders;
            queue.retain(|o| {
                if o.quantity == 0 {
                    orders.remove(&o.id);
                }
                o.quantity != 0
            });
            if queue.is_empty() {
                side.remove(&price);
            }
            if order.quantity == 0 {
                break;
            }
        }
        if order.quantity != 0 && rest {
            self.orders.insert(order.id, (buying, order.price));
            (if buying { &mut self.bids } else { &mut self.asks }).entry(order.price).or_default().push(order.clone());
        }
    }

    fn cancel(&mut self, id: u64) -> Option<SimOrder> {
        let (buying, price) = self.orders.remove(&id)?;
        let side = if buying { &mut self.bids } else { &mut self.asks };
        let queue = side.get_mut(&price)?;
        let k = queue.iter().position(|o| o.id == id)?;
        let order = queue.remove(k);
        if queue.is_empty() {
            side.remove(&price);
        }
        Some(order)
    }

    fn find(&self, id: u64) -> Option<&SimOrder> {
        let &(buying, price) = self.orders.get(&id)?;
        (if buying { &self.bids } else { &self.asks }).get(&price)?.iter().find(|o| o.id == id)
    }

    /// The top DEPTH levels a side, without `hide`'s own orders.
    fn snapshot(&self, hide: Option<Owner>) -> Book {
        fn levels<'a>(prices: impl Iterator<Item = (&'a i64, &'a Vec<SimOrder>)>, hide: Option<Owner>) -> Vec<(i64, i64)> {
            let mut out = Vec::new();
            for (&price, queue) in prices {
                let volume: i64 = queue.iter().filter(|o| Some(o.owner) != hide).map(|o| o.quantity.abs()).sum();
                if volume != 0 {
                    out.push((price, volume));
                    if out.len() == DEPTH {
                        break;
                    }
                }
            }
            out
        }
        Book { bids: levels(self.bids.iter().rev(), hide), asks: levels(self.asks.iter(), hide) }
    }
}

// ---------------------------------------------------------------------------- the agents

fn poisson(rng: &mut PyRandom, rate: f64) -> usize {
    if rate <= 0.0 {
        return 0;
    }
    let (limit, mut k, mut p) = (unsafe { exp(-rate) }, 0, rng.random());
    while p > limit {
        k += 1;
        p *= rng.random();
    }
    k
}

/// `_mid`: the mid, or a one-sided book's best price (an int in Python), or None.
fn mid_of(book: &Book) -> Option<Num> {
    if let Some(mid) = book.mid() {
        return Some(Num::Float(mid));
    }
    book.bids.first().or(book.asks.first()).map(|l| Num::Int(l.0))
}

const FUNDAMENTAL: usize = 5;
const ARRIVAL: usize = 6;

/// One product's fundamental, agents and book (`_Product`).
struct ProductState {
    spec: ProductSpec,
    k: usize, // its index in the spec
    regime_tick: Option<i64>,
    level_shift: f64,
    book: SimBook,
    rngs: Vec<PyRandom>, // the five agent kinds, then the fundamental's and the arrivals'
    value: f64,
    jumps: Vec<(i64, f64)>,        // (tick it snaps back at, size)
    last_jump: Option<(i64, f64)>, // (tick, size)
    last_noise_buy: Option<bool>,
    maker_quotes: Vec<u64>,
    maker_inventory: i64,
    mids: Vec<Num>,
}

impl ProductState {
    fn new(spec: &ProductSpec, k: usize, seed: i64, ticks: usize) -> Self {
        let f = &spec.fundamental;
        let kinds = AGENTS.iter().map(|a| a.name()).chain(["fundamental", "arrival"]);
        ProductState {
            spec: spec.clone(),
            k,
            regime_tick: f.regime_at.map(|at| (at * ticks as f64).round_ties_even() as i64),
            level_shift: 0.0,
            book: SimBook::default(),
            rngs: kinds.map(|kind| PyRandom::from_str(&format!("{seed}/{}/{kind}", spec.name))).collect(),
            value: f.start,
            jumps: Vec::new(),
            last_jump: None,
            last_noise_buy: None,
            maker_quotes: Vec::new(),
            maker_inventory: 0,
            mids: Vec::new(),
        }
    }

    fn step_fundamental(&mut self, tick: i64) {
        let f = &self.spec.fundamental;
        if let Some(at) = self.regime_tick {
            if tick >= at {
                let step = (if tick == at { f.regime_shift } else { 0.0 }) + f.regime_drift;
                self.value += step;
                self.level_shift += step;
            }
        }
        let level = f.level.unwrap_or(f.start) + self.level_shift;
        let rng = &mut self.rngs[FUNDAMENTAL];
        let (shock, jump_draw, jump_sign) = (rng.gauss(0.0, 1.0), rng.random(), rng.random());
        self.value += f.reversion * (level - self.value) + f.sd * shock + f.drift;
        let mut rate = f.jump_rate;
        if f.jump_excite != 0.0 {
            if let Some((at, _)) = self.last_jump {
                rate += f.jump_excite * py::powf(f.jump_decay, (tick - at - 1) as f64);
            }
        }
        if rate != 0.0 && jump_draw < rate {
            let size = match (f.jump_reverse, self.last_jump) {
                (Some(reverse), Some((_, last))) => {
                    if jump_sign < reverse {
                        -last
                    } else {
                        last
                    }
                }
                _ => {
                    if jump_sign < 0.5 {
                        f.jump_size
                    } else {
                        -f.jump_size
                    }
                }
            };
            self.value += size;
            self.last_jump = Some((tick, size));
            if let Some(back) = f.snap_back {
                self.jumps.push((tick + back, size));
            }
        }
        for &(at, size) in &self.jumps {
            if at == tick {
                self.value -= size;
            }
        }
        self.jumps.retain(|&(at, _)| at != tick);
    }

    /// This tick's arrivals: the quoters, who come before the snapshot, and the takers, after the bots.
    fn arrivals(&mut self) -> (Vec<Kind>, Vec<Kind>) {
        let s = &self.spec;
        let maker = self.rngs[0].random() < s.maker.refresh;
        let mut quoters = vec![Kind::Limit; poisson(&mut self.rngs[1], s.limit_traders.rate)];
        let mut takers = Vec::new();
        for (j, kind, rate) in [(2, Kind::Noise, s.noise.rate), (3, Kind::Value, s.value.rate), (4, Kind::Momentum, s.momentum.rate)] {
            let n = poisson(&mut self.rngs[j], rate);
            takers.extend(std::iter::repeat(kind).take(n));
        }
        if maker {
            if s.maker.first {
                quoters.insert(0, Kind::Maker);
            } else {
                takers.push(Kind::Maker);
            }
        }
        self.rngs[ARRIVAL].shuffle(&mut takers);
        (quoters, takers)
    }

    /// One agent's arrival: its orders, each submitted (pushing its matches onto `out`, after the order).
    fn act(&mut self, kind: Kind, tick: i64, timestamp: i64, next_id: &mut u64, out: &mut Vec<(SimOrder, Vec<Match>)>) {
        let mut new_id = || {
            let id = *next_id;
            *next_id += 1;
            id
        };
        let (s, k) = (&self.spec, self.k);
        let mut orders: Vec<(SimOrder, bool)> = Vec::new(); // (order, rests)
        let owner = Owner::Agent(kind);
        match kind {
            Kind::Maker => {
                let m = &s.maker;
                let rng = &mut self.rngs[0];
                let (noise, bid_size, ask_size) = (rng.gauss(0.0, 1.0), rng.randint(m.size.0, m.size.1), rng.randint(m.size.0, m.size.1));
                for &id in &self.maker_quotes {
                    self.book.cancel(id);
                }
                let centre = self.value + m.noise * noise - m.skew * self.maker_inventory as f64;
                let bid = py::round(centre - m.half_spread);
                let mut ask = py::round(centre + m.half_spread);
                if ask <= bid {
                    ask = bid + 1;
                }
                let quotes = [SimOrder::new(new_id(), owner, k, bid, bid_size, timestamp, None), SimOrder::new(new_id(), owner, k, ask, -ask_size, timestamp, None)];
                self.maker_quotes = quotes.iter().map(|q| q.id).collect();
                orders = quotes.into_iter().map(|q| (q, true)).collect();
            }
            Kind::Limit => {
                let t = &s.limit_traders;
                let rng = &mut self.rngs[1];
                let (buying, offset, noise, size) = (rng.random() < 0.5, rng.uniform(t.offset.0, t.offset.1), rng.gauss(0.0, 1.0), rng.randint(t.size.0, t.size.1));
                let view = self.value + t.noise * noise;
                let price = if buying { (view - offset).floor() } else { (view + offset).ceil() } as i64;
                orders.push((SimOrder::new(new_id(), owner, k, price, if buying { size } else { -size }, timestamp, Some(tick + t.life)), true));
            }
            Kind::Noise => {
                let t = &s.noise;
                let rng = &mut self.rngs[2];
                let mut buying = rng.random() < t.buy_share;
                if t.persistence != 0.0 && rng.random() < t.persistence {
                    if let Some(last) = self.last_noise_buy {
                        buying = last;
                    }
                }
                self.last_noise_buy = Some(buying);
                let (low, high) = if buying { t.size } else { t.sell_size.unwrap_or(t.size) };
                let size = rng.randint(low, high);
                let touch = if buying { self.book.best_ask() } else { self.book.best_bid() };
                if let Some(price) = touch {
                    orders.push((SimOrder::new(new_id(), owner, k, price, if buying { size } else { -size }, timestamp, None), false));
                }
            }
            Kind::Value => {
                let t = &s.value;
                let rng = &mut self.rngs[3];
                let (noise, size) = (rng.gauss(0.0, 1.0), rng.randint(t.size.0, t.size.1));
                let view = self.value + t.noise * noise;
                let (ask, bid) = (self.book.best_ask(), self.book.best_bid());
                if ask.is_some_and(|a| a as f64 <= view - t.threshold) {
                    orders.push((SimOrder::new(new_id(), owner, k, (view - t.threshold).floor() as i64, size, timestamp, None), false));
                } else if bid.is_some_and(|b| b as f64 >= view + t.threshold) {
                    orders.push((SimOrder::new(new_id(), owner, k, (view + t.threshold).ceil() as i64, -size, timestamp, None), false));
                }
            }
            Kind::Momentum => {
                let t = &s.momentum;
                let size = self.rngs[4].randint(t.size.0, t.size.1);
                if self.mids.len() >= t.long {
                    let n = self.mids.len();
                    let short = py::sum_num(&self.mids[n.saturating_sub(t.short)..]).div(t.short as i64);
                    let long = py::sum_num(&self.mids[n.saturating_sub(t.long)..]).div(t.long as i64);
                    let signal = short - long;
                    let (ask, bid) = (self.book.best_ask(), self.book.best_bid());
                    if signal >= t.threshold && ask.is_some() {
                        orders.push((SimOrder::new(new_id(), owner, k, ask.unwrap(), size, timestamp, None), false));
                    } else if signal <= -t.threshold && bid.is_some() {
                        orders.push((SimOrder::new(new_id(), owner, k, bid.unwrap(), -size, timestamp, None), false));
                    }
                }
            }
        }
        for (mut order, rests) in orders {
            let mut matches = Vec::new();
            self.book.submit(&mut order, rests, false, &mut matches);
            out.push((order, matches));
        }
    }

    fn expire(&mut self, tick: i64) {
        let gone: Vec<u64> = self.book.bids.values().chain(self.book.asks.values()).flatten().filter(|o| o.expires.is_some_and(|e| e <= tick)).map(|o| o.id).collect();
        for id in gone {
            self.book.cancel(id);
        }
    }

    /// The snapshot's mid for the momentum takers' history (the last one again if the book is empty).
    fn snapshot_mid(&mut self, book: &Book) -> Option<Num> {
        let mid = mid_of(book);
        match mid {
            Some(m) => self.mids.push(m),
            None => {
                if let Some(&last) = self.mids.last() {
                    self.mids.push(last);
                }
            }
        }
        mid
    }
}

// ---------------------------------------------------------------------------- the market

struct Player {
    result: DayResult,
    position: Vec<i64>, // per product (sorted index)
    cash: Vec<f64>,
    unseen_fills: Vec<Fill>,
    live: Vec<(u64, usize)>, // its orders on the book (id, spec index of the product), oldest first
}

/// A trade as the market logs it: product (spec index), price, volume, buyer, seller.
#[derive(Clone, Copy)]
struct Logged {
    k: usize,
    price: i64,
    volume: i64,
    buyer: Owner,
    seller: Owner,
    timestamp: i64,
}

pub struct SimDay {
    /// The snapshots and the agents' trades with each other, as a recording. Each tick's trades
    /// are also kept in the order they happened, across products, in `logged`.
    pub day: Day,
    pub logged: Vec<Vec<MarketTrade>>,
    /// Per product (sorted index), the fundamental at each snapshot.
    pub fundamentals: Vec<Vec<f64>>,
    /// Per tick and product (sorted index), the recorded mark as Python holds it (an int for a one-sided book).
    pub marks: Vec<Vec<Option<Num>>>,
    pub results: Vec<DayResult>,
}

/// The market's name table: the empty name, the bots, then the agent kinds.
pub fn names_table(bots: &[String]) -> Vec<String> {
    let mut names = vec![String::new()];
    names.extend(bots.iter().cloned());
    names.extend(AGENTS.iter().map(|a| a.name().to_string()));
    names
}

struct Market<'a> {
    spec: &'a MarketSpec,
    sorted: Vec<usize>, // spec index -> sorted index
    nbots: usize,
    products: Vec<ProductState>,
    players: Vec<Player>,
}

impl Market<'_> {
    /// `_shown`: bots by name, agents by kind only if spec.names.
    fn shown(&self, owner: Owner) -> Name {
        match owner {
            Owner::Bot(i) => 1 + i as Name,
            Owner::Agent(kind) if self.spec.names => (1 + self.nbots + AGENTS.iter().position(|&a| a == kind).unwrap()) as Name,
            Owner::Agent(_) => 0,
        }
    }

    fn named(&self, t: &Logged) -> MarketTrade {
        MarketTrade { product: self.sorted[t.k], price: t.price, quantity: t.volume, buyer: self.shown(t.buyer), seller: self.shown(t.seller), timestamp: t.timestamp }
    }

    /// `execute`: books one match for both sides.
    fn execute(&mut self, incoming: &SimOrder, m: &Match, timestamp: i64, log: &mut Vec<Logged>) {
        let there = (m.id, m.owner, m.left);
        let mine = (incoming.id, incoming.owner, incoming.quantity);
        let (buyer, seller) = if incoming.buying { (mine, there) } else { (there, mine) };
        let p = self.sorted[incoming.product];
        for ((id, owner, left), other, sign) in [(buyer, seller.1, 1), (seller, buyer.1, -1)] {
            match owner {
                Owner::Agent(Kind::Maker) => self.products[incoming.product].maker_inventory += sign * m.volume,
                Owner::Bot(i) => {
                    let source = if id == incoming.id { Source::Book } else { Source::Trade };
                    let fill = Fill { timestamp, product: p, price: m.price, quantity: sign * m.volume, source, counterparty: self.shown(other), order_id: id };
                    let player = &mut self.players[i];
                    player.position[p] += sign * m.volume;
                    player.cash[p] -= (m.price * sign * m.volume) as f64;
                    player.result.fills.push(fill);
                    player.unseen_fills.push(fill);
                    if left == 0 {
                        player.live.retain(|&(o, _)| o != id);
                    }
                }
                Owner::Agent(_) => {}
            }
        }
        log.push(Logged { k: incoming.product, price: m.price, volume: m.volume, buyer: buyer.1, seller: seller.1, timestamp });
    }
}

fn view(order: &SimOrder, p: usize) -> OpenOrder {
    OpenOrder { id: order.id, product: p, price: order.price, quantity: order.quantity, timestamp: order.timestamp }
}

/// Runs the market for one day, with the bots (if any) trading inside it (`run`).
pub fn run(spec: &MarketSpec, seed: i64, bots: &mut [(String, &mut dyn Bot)], resting: bool, name: Option<&str>) -> Result<SimDay, String> {
    let bot_names: Vec<String> = bots.iter().map(|(n, _)| n.clone()).collect();
    let mut unique = bot_names.clone();
    unique.sort_unstable();
    unique.dedup();
    if unique.len() != bot_names.len() || bot_names.iter().any(|n| AGENTS.iter().any(|a| a.name() == n)) {
        return Err(format!("bot names must be unique and not an agent kind: {bot_names:?}"));
    }
    let n = spec.products.len();
    let mut by_name: Vec<usize> = (0..n).collect();
    by_name.sort_by(|&a, &b| spec.products[a].name.cmp(&spec.products[b].name));
    let mut sorted = vec![0; n];
    for (p, &k) in by_name.iter().enumerate() {
        sorted[k] = p;
    }
    let names = names_table(&bot_names);
    let day_name = name.map_or_else(|| format!("sim{seed}"), str::to_string);
    let shell = Day {
        name: day_name.clone(),
        products: by_name.iter().map(|&k| spec.products[k].name.clone()).collect(),
        limits: by_name.iter().map(|&k| spec.products[k].limit).collect(),
        order: sorted.clone(),
        limits_order: sorted.clone(),
        info: vec![None; n],
        ticks: Vec::new(),
        names: names.clone(),
    };
    let limits = shell.limits.clone();
    for (_, bot) in bots.iter_mut() {
        bot.begin_day(&shell, &names);
    }
    let mut market = Market {
        spec,
        sorted: sorted.clone(),
        nbots: bots.len(),
        products: spec.products.iter().enumerate().map(|(k, p)| ProductState::new(p, k, seed, spec.ticks)).collect(),
        players: (0..bots.len())
            .map(|_| Player { result: new_result(&shell), position: vec![0; n], cash: vec![0.0; n], unseen_fills: Vec::new(), live: Vec::new() })
            .collect(),
    };
    let mut arrival = PyRandom::from_str(&format!("{seed}/bots"));
    let mut next_id: u64 = 1;
    let mut ticks: Vec<Tick> = Vec::with_capacity(spec.ticks);
    let mut logged_days: Vec<Vec<MarketTrade>> = Vec::with_capacity(spec.ticks);
    let mut fundamentals: Vec<Vec<f64>> = vec![Vec::with_capacity(spec.ticks); n];
    let mut all_marks: Vec<Vec<Option<Num>>> = Vec::with_capacity(spec.ticks);
    let mut marks = vec![0.0f64; n]; // per sorted product
    let mut since: Vec<Logged> = Vec::new(); // every trade since the bots' last call
    let mut buffer = Vec::new();
    let mut scratch = BotScratch { buys: vec![0; n], sells: vec![0; n], ..Default::default() };

    for tick in 0..spec.ticks as i64 {
        let timestamp = tick * spec.step;
        let mut executed: Vec<Logged> = Vec::new();
        let mut takers = Vec::with_capacity(n);
        for k in 0..n {
            let state = &mut market.products[k];
            state.expire(tick);
            state.step_fundamental(tick);
            let (quoters, t) = state.arrivals();
            takers.push(t);
            for kind in quoters {
                buffer.clear();
                market.products[k].act(kind, tick, timestamp, &mut next_id, &mut buffer);
                for (order, matches) in buffer.drain(..) {
                    for m in &matches {
                        market.execute(&order, m, timestamp, &mut executed);
                    }
                }
            }
        }

        let mut books: Vec<Option<Book>> = vec![None; n];
        let mut tick_marks: Vec<Option<Num>> = vec![None; n];
        for k in 0..n {
            let p = sorted[k];
            let book = market.products[k].book.snapshot(None);
            fundamentals[p].push(market.products[k].value);
            let mid = market.products[k].snapshot_mid(&book);
            if let Some(mid) = mid {
                marks[p] = mid.f64();
            }
            tick_marks[p] = mid;
            books[p] = Some(book);
        }

        let quoted = executed.len();
        if !market.players.is_empty() {
            let mut seen = std::mem::take(&mut since);
            seen.extend_from_slice(&executed);
            bots_trade(&mut market, bots, &books, &seen, &marks, timestamp, &limits, resting, &mut arrival, &mut next_id, &mut executed, &mut scratch);
        }
        for k in 0..n {
            for kind in std::mem::take(&mut takers[k]) {
                buffer.clear();
                market.products[k].act(kind, tick, timestamp, &mut next_id, &mut buffer);
                for (order, matches) in buffer.drain(..) {
                    for m in &matches {
                        market.execute(&order, m, timestamp, &mut executed);
                    }
                }
            }
        }
        since = executed[quoted..].to_vec(); // the bots see these next tick
        if !resting {
            // the bots' orders lived for this tick's takers only
            for player in market.players.iter_mut() {
                for (id, k) in player.live.drain(..) {
                    market.products[k].book.cancel(id);
                }
            }
        }
        let recorded: Vec<MarketTrade> = executed.iter().filter(|t| !matches!(t.buyer, Owner::Bot(_)) && !matches!(t.seller, Owner::Bot(_))).map(|t| market.named(t)).collect();
        let mut trades: Vec<Vec<MarketTrade>> = vec![Vec::new(); n];
        for t in &recorded {
            trades[t.product].push(*t);
        }
        let tick_data = Tick { timestamp, books, order: sorted.clone(), trades, marks: tick_marks.iter().map(|m| m.map(Num::f64)).collect() };
        for player in market.players.iter_mut() {
            record(player, &tick_data, &marks);
        }
        ticks.push(tick_data);
        logged_days.push(recorded);
        all_marks.push(tick_marks);
    }
    let recorded: Vec<(i64, MarketTrade)> = ticks.iter().flat_map(|t| t.trades.iter().flatten().map(move |&tr| (t.timestamp, tr))).collect();
    let mut results: Vec<DayResult> = market.players.into_iter().map(|p| p.result).collect();
    for result in results.iter_mut() {
        result.market_trades = recorded.clone();
    }
    Ok(SimDay { day: Day { ticks, ..shell }, logged: logged_days, fundamentals, marks: all_marks, results })
}

fn record(player: &mut Player, tick: &Tick, marks: &[f64]) {
    let result = &mut player.result;
    result.timestamps.push(tick.timestamp);
    for p in 0..marks.len() {
        result.positions[p].push(player.position[p]);
        result.marks[p].push(marks[p]);
        result.pnl[p].push(player.cash[p] + player.position[p] as f64 * marks[p]);
        let book = tick.books[p].as_ref();
        result.best_bids[p].push(book.and_then(|b| b.bids.first().map(|l| l.0)));
        result.best_asks[p].push(book.and_then(|b| b.asks.first().map(|l| l.0)));
        result.wall_mids[p].push(book.and_then(Book::wall_mid));
    }
}

#[derive(Default)]
struct BotScratch {
    orders: Vec<Order>,
    buys: Vec<i64>,
    sells: Vec<i64>,
    breached: Vec<usize>,
    raced: Vec<usize>,
}

/// `_bots_trade`: the bots see the snapshot and the trades since their last call, decide at once,
/// and their actions reach the book in a seeded random order, as in engine.run_market.
#[allow(clippy::too_many_arguments)]
fn bots_trade(
    market: &mut Market,
    bots: &mut [(String, &mut dyn Bot)],
    books: &[Option<Book>],
    since: &[Logged],
    marks: &[f64],
    timestamp: i64,
    limits: &[i64],
    resting: bool,
    arrival: &mut PyRandom,
    next_id: &mut u64,
    executed: &mut Vec<Logged>,
    s: &mut BotScratch,
) {
    let _ = marks;
    let n = books.len();
    let mut actions: Vec<Vec<Action>> = Vec::with_capacity(bots.len());
    let mut decided: Vec<(Vec<i64>, Vec<OpenOrder>)> = Vec::with_capacity(bots.len());
    let order: Vec<usize> = market.sorted.clone();
    for (i, (_, bot)) in bots.iter_mut().enumerate() {
        let seen_books: Vec<Option<Book>> = if resting {
            let mut out = vec![None; n];
            for (k, state) in market.products.iter().enumerate() {
                out[market.sorted[k]] = Some(state.book.snapshot(Some(Owner::Bot(i))));
            }
            out
        } else {
            books.to_vec()
        };
        let mut market_trades: Vec<Vec<MarketTrade>> = vec![Vec::new(); n];
        for t in since.iter().filter(|t| t.buyer != Owner::Bot(i) && t.seller != Owner::Bot(i)) {
            let named = market.named(t);
            market_trades[named.product].push(named);
        }
        let mine = live_views(market, i);
        let view = TickView { timestamp, books: &seen_books, order: &order };
        let player = &mut market.players[i];
        let mut out = Vec::new();
        bot.step(&view, &player.position, &player.unseen_fills, &market_trades, &mine, &mut out);
        if let Some(error) = bot.failed() {
            out.clear();
            player.result.errors.push((timestamp, error));
        }
        actions.push(out);
        decided.push((player.position.clone(), mine));
        player.unseen_fills.clear();
    }

    let mut order_of_arrival: Vec<usize> = (0..bots.len()).collect();
    arrival.shuffle(&mut order_of_arrival);
    for i in order_of_arrival {
        let (seen_position, seen) = &decided[i];
        s.orders.clear();
        let mut cancelled: Vec<u64> = Vec::new();
        for action in &actions[i] {
            match *action {
                Action::Order(o) => s.orders.push(o),
                Action::Cancel(id) => {
                    if let Some(at) = market.players[i].live.iter().position(|&(o, _)| o == id) {
                        let (_, k) = market.players[i].live.remove(at);
                        market.products[k].book.cancel(id);
                        cancelled.push(id);
                        market.players[i].result.cancels.push((timestamp, id));
                    } else if !seen.iter().any(|o| o.id == id) {
                        let hint = if resting { "" } else { " (orders only rest in resting mode)" };
                        market.players[i].result.errors.push((timestamp, format!("cancel for order {id}, which isn't open{hint}")));
                    }
                }
            }
        }
        known(&mut s.orders, n, timestamp, &mut market.players[i].result, &*bots[i].1);
        let kept = live_views(market, i);
        let seen_left = seen.iter().filter(|o| !cancelled.contains(&o.id)).map(|o| (o.product, o.quantity));
        breaches(&s.orders, seen_position, seen_left, limits, &mut s.buys, &mut s.sells, &mut s.breached);
        let player = &market.players[i];
        breaches(&s.orders, &player.position, kept.iter().map(|o| (o.product, o.quantity)), limits, &mut s.buys, &mut s.sells, &mut s.raced);
        let breached = s.breached.clone();
        s.raced.retain(|p| !breached.contains(p));
        let result = &mut market.players[i].result;
        result.limit_breaches.extend(s.breached.iter().map(|&p| (timestamp, p)));
        result.races.extend(s.raced.iter().map(|&p| (timestamp, p)));
        let mut placed = Vec::new();
        for o in s.orders.iter() {
            if s.breached.contains(&o.product) || s.raced.contains(&o.product) {
                continue;
            }
            let k = market.sorted.iter().position(|&p| p == o.product).unwrap();
            let mut live = SimOrder::new(*next_id, Owner::Bot(i), k, o.price, o.quantity, timestamp, None);
            *next_id += 1;
            placed.push(view(&live, o.product));
            let rests = !(resting && o.ioc);
            let mut matches = Vec::new();
            market.products[k].book.submit(&mut live, rests, true, &mut matches);
            for m in &matches {
                market.execute(&live, m, timestamp, executed);
            }
            if live.quantity != 0 && rests {
                market.players[i].live.push((live.id, k));
            }
        }
        let result = &mut market.players[i].result;
        result.orders.extend(kept.into_iter().chain(placed).map(|o| (timestamp, o)));
    }
}

/// A bot's orders on the book, oldest first, as it sees them.
fn live_views(market: &Market, i: usize) -> Vec<OpenOrder> {
    market.players[i]
        .live
        .iter()
        .filter_map(|&(id, k)| market.products[k].book.find(id).map(|o| view(o, market.sorted[k])))
        .collect()
}

// ---------------------------------------------------------------------------- files

/// `write_day` without limits.json (Python merges that): the day's prices, trades and fundamental
/// in the Prosperity layout, written as Python's csv module writes them (";", "\r\n").
pub fn write_csvs(sim: &SimDay, dir: &std::path::Path, round: i64, day: i64) -> Result<(), String> {
    use std::fmt::Write as _;
    let folder = dir.join(format!("round{round}"));
    std::fs::create_dir_all(&folder).map_err(|e| format!("{}: {e}", folder.display()))?;
    let stem = format!("round_{round}_day_{day}");
    let d = &sim.day;
    let mut prices = String::from("day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;");
    prices.push_str("ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss\r\n");
    let mut trades = String::from("timestamp;buyer;seller;symbol;currency;price;quantity\r\n");
    let mut fundamental = String::from("timestamp;product;value\r\n");
    for (k, tick) in d.ticks.iter().enumerate() {
        for &p in &d.order {
            let book = tick.books[p].as_ref().unwrap();
            let _ = write!(prices, "{day};{};{}", tick.timestamp, d.products[p]);
            for levels in [&book.bids, &book.asks] {
                for j in 0..DEPTH {
                    match levels.get(j) {
                        Some((price, volume)) => write!(prices, ";{price};{volume}"),
                        None => write!(prices, ";;"),
                    }
                    .unwrap();
                }
            }
            match sim.marks[k][p] {
                Some(mark) => write!(prices, ";{:.1};0.0\r\n", mark.f64()),
                None => write!(prices, ";;0.0\r\n"),
            }
            .unwrap();
            for t in &tick.trades[p] {
                let _ = write!(trades, "{};{};{};{};SEASHELLS;{:.1};{}\r\n", tick.timestamp, d.names[t.buyer as usize], d.names[t.seller as usize], d.products[p], t.price as f64, t.quantity);
            }
            let _ = write!(fundamental, "{};{};{:.3}\r\n", tick.timestamp, d.products[p], sim.fundamentals[p][k]);
        }
    }
    for (kind, text) in [("prices", prices), ("trades", trades), ("fundamental", fundamental)] {
        let path = folder.join(format!("{kind}_{stem}.csv"));
        std::fs::write(&path, text).map_err(|e| format!("{}: {e}", path.display()))?;
    }
    Ok(())
}
