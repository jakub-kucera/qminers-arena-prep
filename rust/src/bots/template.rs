//! python/bots/template.py in Rust: its STRATEGY and EXECUTION, function for function with the Python
//! names, and its ADAPTER as the Prosperity format plug-in presents the engine's tick to it. Keep
//! the two equal: python/tests/test_rust.py checks that both trade the same, and rust/twins.json holds the
//! hash of the Python file the port was last checked against.
//!
//! python/bots/drill/template.py is the same STRATEGY and EXECUTION behind the drill format's ADAPTER
//! (`Template::drill`): prices in each product's ticks, converted from and to the format's price
//! units as its plug-in and ADAPTER do (python/arena/formats/drill.py), products in the exchange's order,
//! trades without names, and each product's limit from the exchange.
//!
//! The settings come from the Python file itself: python/arena/rust.py loads it (with any --set overrides)
//! and passes its DEFAULTS and PARAMS, so `params_for` here merges them as Python's does. Floats are
//! computed in the same order as Python's, with the same libm calls (`x ** 2` is libm's `pow`, which
//! on macOS isn't always `x * x`; NormalDist's cdf is libm's `erf`), so the PnL matches to the bit.
//!
//! Not ported: STRICT (a Rust bot can't raise into the result), the per-product try/except, and
//! `param_conflicts` (a check that arena.validate calls; it doesn't trade).
//! Settings the Python file would only fail on at run time (an unknown key, an unknown fair method,
//! a float where the strategy needs an integer) are refused when the bot is built.

use std::f64::consts::SQRT_2;
use std::hint::black_box;

use crate::arena::engine::{Bot, TickView};
use crate::support::json::Value;
use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, Name, OpenOrder, Order, Price};

extern "C" {
    fn erf(x: f64) -> f64;
    fn pow(x: f64, y: f64) -> f64;
}

/// Python's `x ** 2` on a float: libm's pow, kept from being folded into x * x.
fn sq(x: f64) -> f64 {
    unsafe { pow(x, black_box(2.0)) }
}

/// statistics.NormalDist().cdf
fn cdf(x: f64) -> f64 {
    0.5 * (1.0 + unsafe { erf(x / SQRT_2) })
}

/// Python's round() of a float: ties to even.
fn round(x: f64) -> i64 {
    x.round_ties_even() as i64
}

// ------------------------------------------------------------------------------ PARAMS

#[derive(Clone, Copy, PartialEq, Debug)]
enum Fair {
    Fixed,
    Mid,
    WallMid,
    OuterMid,
    SizedMid,
    WeightedMid,
    HysteresisMid,
}

#[derive(Clone, PartialEq, Debug)]
enum Level {
    Off,
    Day,
    At(f64),
}

#[derive(Clone, Copy, PartialEq, Debug)]
enum CpdAction {
    Level,
    Drop,
    Other,
}

/// One product's settings, {**DEFAULTS, **PARAMS[product]}, typed.
#[derive(Clone, Debug)]
struct P {
    limit: i64,
    fair: Fair,
    fixed_fair: Option<f64>,
    fixed_guard: Option<f64>,
    wall_size: f64,
    smoothing: f64,
    imbalance: f64,
    lin_rho3: f64,
    lin_momentum: f64,
    lin_window: i64,
    gate_move: Option<f64>,
    gate_window: i64,
    take_edge: f64,
    clear_edge: f64,
    make_edge: f64,
    make_inside: Option<i64>,
    skew: f64,
    size_skew: f64,
    target: i64,
    make_size: Option<i64>,
    take_edge_buy: Option<f64>,
    take_edge_sell: Option<f64>,
    make_edge_buy: Option<f64>,
    make_edge_sell: Option<f64>,
    make_levels: i64,
    make_step: i64,
    take_reserve: i64,
    join_min: Option<f64>,
    join_ratio: f64,
    cross_max: Option<i64>,
    cross_excess: Option<i64>,
    level: Level,
    level_weight: Option<f64>,
    level_band: f64,
    level_exit: Option<f64>,
    level_guard: Option<f64>,
    cpd_hazard: Option<f64>,
    cpd_reversion: f64,
    cpd_sd: f64,
    cpd_block: i64,
    cpd_action: CpdAction,
    cpd_threshold: f64,
    follow: Option<String>,
    strike: f64,
    max_cost_per_delta: f64,
    smile: Option<(f64, f64, f64)>,
    underlying: Option<String>,
    expiry: f64,
    day_length: f64,
    smile_window: f64,
    basket: Option<Vec<(String, f64)>>,
    hedge_ratio: f64,
    hedge: bool,
    jump_min: Option<f64>,
    jump_hold: Option<f64>,
    jump_edge: f64,
    jump_seen: f64,
    jump_share: f64,
    copy: Option<Vec<(String, f64)>>,
    copy_sizes: Option<Vec<i64>>,
    copy_warmup: i64,
    copy_hold: Option<f64>,
    copy_edge: f64,
    stop_loss: Option<f64>,
    stop_edge: Option<f64>,
    flatten_from: Option<f64>,
    flatten_edge: Option<f64>,
    flatten_keep: Option<f64>,
    flatten_widen: f64,
    reduce_only: bool,
    vol_guard: Option<f64>,
    // The names above as the day's product indices (None: not on the day), set by begin_day.
    follow_id: Option<usize>,
    underlying_id: Option<usize>,
    basket_ids: Vec<Option<usize>>,
}

struct Reader<'a> {
    product: &'a str,
    items: &'a [(String, Value)],
}

impl Reader<'_> {
    fn value(&self, key: &str) -> Result<&Value, String> {
        self.items.iter().rev().find(|(k, _)| k == key).map(|(_, v)| v).ok_or_else(|| format!("{}: no {key} in DEFAULTS", self.product))
    }

    fn fail<T>(&self, key: &str, what: &str) -> Result<T, String> {
        Err(format!("{}: {key} must be {what} for the Rust template, got {:?}", self.product, self.value(key).ok()))
    }

    fn num(&self, key: &str) -> Result<f64, String> {
        match self.value(key)? {
            v @ (Value::Int(_) | Value::Float(_) | Value::Bool(_)) => Ok(v.as_f64().unwrap()),
            _ => self.fail(key, "a number"),
        }
    }

    fn opt_num(&self, key: &str) -> Result<Option<f64>, String> {
        if self.value(key)?.is_null() {
            Ok(None)
        } else {
            self.num(key).map(Some)
        }
    }

    fn int(&self, key: &str) -> Result<i64, String> {
        match self.value(key)?.as_i64() {
            Some(v) => Ok(v),
            None => self.fail(key, "an integer"),
        }
    }

    fn opt_int(&self, key: &str) -> Result<Option<i64>, String> {
        if self.value(key)?.is_null() {
            Ok(None)
        } else {
            self.int(key).map(Some)
        }
    }

    fn opt_str(&self, key: &str) -> Result<Option<String>, String> {
        match self.value(key)? {
            Value::Null => Ok(None),
            Value::Str(s) => Ok(Some(s.clone())),
            _ => self.fail(key, "a product name or None"),
        }
    }

    fn weights(&self, key: &str) -> Result<Option<Vec<(String, f64)>>, String> {
        match self.value(key)? {
            Value::Null => Ok(None),
            Value::Object(items) => items
                .iter()
                .map(|(k, v)| v.as_f64().map(|w| (k.clone(), w)).ok_or_else(|| format!("{}: {key}[{k}] must be a number", self.product)))
                .collect::<Result<_, _>>()
                .map(Some),
            _ => self.fail(key, "a dict of numbers or None"),
        }
    }
}

impl P {
    fn read(product: &str, items: &[(String, Value)]) -> Result<P, String> {
        let r = Reader { product, items };
        let fair = match r.value("fair")?.as_str() {
            Some("fixed") => Fair::Fixed,
            Some("mid") => Fair::Mid,
            Some("wall_mid") => Fair::WallMid,
            Some("outer_mid") => Fair::OuterMid,
            Some("sized_mid") => Fair::SizedMid,
            Some("weighted_mid") => Fair::WeightedMid,
            Some("hysteresis_mid") => Fair::HysteresisMid,
            _ => return r.fail("fair", "a known fair value method"),
        };
        let level = match r.value("level")? {
            Value::Null => Level::Off,
            Value::Str(s) if s == "day" => Level::Day,
            Value::Int(_) | Value::Float(_) => Level::At(r.num("level")?),
            _ => return r.fail("level", "a number, \"day\" or None"),
        };
        let cpd_action = match r.value("cpd_action")?.as_str() {
            Some("level") => CpdAction::Level,
            Some("drop") => CpdAction::Drop,
            _ => CpdAction::Other,
        };
        let smile = match r.value("smile")? {
            Value::Null => None,
            Value::List(v) if v.len() == 3 && v.iter().all(|x| x.as_f64().is_some()) => Some((v[0].as_f64().unwrap(), v[1].as_f64().unwrap(), v[2].as_f64().unwrap())),
            _ => return r.fail("smile", "(a, b, c) or None"),
        };
        let needs = |on: bool, key: &str| -> Result<f64, String> { if on { r.num(key) } else { Ok(r.opt_num(key)?.unwrap_or(f64::NAN)) } };
        let follow = r.opt_str("follow")?;
        Ok(P {
            limit: r.int("limit")?,
            fair,
            fixed_fair: r.opt_num("fixed_fair")?,
            fixed_guard: r.opt_num("fixed_guard")?,
            wall_size: r.num("wall_size")?,
            smoothing: r.num("smoothing")?,
            imbalance: r.num("imbalance")?,
            lin_rho3: r.num("lin_rho3")?,
            lin_momentum: r.num("lin_momentum")?,
            lin_window: r.int("lin_window")?,
            gate_move: r.opt_num("gate_move")?,
            gate_window: r.int("gate_window")?,
            take_edge: r.num("take_edge")?,
            clear_edge: r.num("clear_edge")?,
            make_edge: r.num("make_edge")?,
            make_inside: r.opt_int("make_inside")?,
            skew: r.num("skew")?,
            size_skew: r.num("size_skew")?,
            target: r.int("target")?,
            make_size: r.opt_int("make_size")?,
            take_edge_buy: r.opt_num("take_edge_buy")?,
            take_edge_sell: r.opt_num("take_edge_sell")?,
            make_edge_buy: r.opt_num("make_edge_buy")?,
            make_edge_sell: r.opt_num("make_edge_sell")?,
            make_levels: r.int("make_levels")?,
            make_step: r.int("make_step")?,
            take_reserve: r.int("take_reserve")?,
            join_min: r.opt_num("join_min")?,
            join_ratio: r.num("join_ratio")?,
            cross_max: r.opt_int("cross_max")?,
            cross_excess: r.opt_int("cross_excess")?,
            level,
            level_weight: r.opt_num("level_weight")?,
            level_band: r.num("level_band")?,
            level_exit: r.opt_num("level_exit")?,
            level_guard: r.opt_num("level_guard")?,
            cpd_hazard: r.opt_num("cpd_hazard")?,
            cpd_reversion: needs(!r.value("cpd_hazard")?.is_null(), "cpd_reversion")?,
            cpd_sd: needs(!r.value("cpd_hazard")?.is_null(), "cpd_sd")?,
            cpd_block: r.int("cpd_block")?,
            cpd_action,
            cpd_threshold: r.num("cpd_threshold")?,
            strike: needs(follow.is_some() || smile.is_some(), "strike")?,
            follow,
            max_cost_per_delta: r.num("max_cost_per_delta")?,
            smile,
            underlying: r.opt_str("underlying")?,
            expiry: needs(smile.is_some(), "expiry")?,
            day_length: r.num("day_length")?,
            smile_window: r.num("smile_window")?,
            basket: r.weights("basket")?,
            hedge_ratio: r.num("hedge_ratio")?,
            hedge: r.value("hedge")?.truthy(),
            jump_min: r.opt_num("jump_min")?,
            jump_hold: r.opt_num("jump_hold")?,
            jump_edge: r.num("jump_edge")?,
            jump_seen: r.num("jump_seen")?,
            jump_share: r.num("jump_share")?,
            copy: r.weights("copy")?,
            copy_sizes: match r.value("copy_sizes")? {
                Value::Null => None,
                Value::List(v) => Some(v.iter().map(|x| x.as_i64().ok_or_else(|| format!("{product}: copy_sizes must hold whole numbers"))).collect::<Result<_, _>>()?),
                _ => return r.fail("copy_sizes", "a list of sizes or None"),
            },
            copy_warmup: r.int("copy_warmup")?,
            copy_hold: r.opt_num("copy_hold")?,
            copy_edge: r.num("copy_edge")?,
            stop_loss: r.opt_num("stop_loss")?,
            stop_edge: r.opt_num("stop_edge")?,
            flatten_from: r.opt_num("flatten_from")?,
            flatten_edge: r.opt_num("flatten_edge")?,
            flatten_keep: r.opt_num("flatten_keep")?,
            flatten_widen: r.num("flatten_widen")?,
            reduce_only: r.value("reduce_only")?.truthy(),
            vol_guard: r.opt_num("vol_guard")?,
            follow_id: None,
            underlying_id: None,
            basket_ids: Vec::new(),
        })
    }
}

/// What trade_product overrides in p for one tick (Python's `p = {**p, ...}`).
#[derive(Clone, Copy)]
struct Eff {
    target: i64,
    take_buy: f64, // take_edge_buy, else take_edge
    take_sell: f64,
    make_buy: f64, // make_edge_buy, else make_edge
    make_sell: f64,
    clear_edge: f64,
    make_size: Option<i64>,
    reduce_only: bool,
    pull: i8, // 1: no ask (the fair just rose), -1: no bid
}

/// One product's memory dict, a field per key; None (or the default) where Python's key is absent.
#[derive(Clone, Default)]
struct Memory {
    fair: Option<f64>,
    hysteresis: Option<f64>,
    trail: Vec<f64>,
    held: i64,
    broken: bool,
    level_sum: f64,
    level_n: i64,
    cp_sum: f64,
    cp_n: i64,
    cp_level: Option<f64>,
    cp_runs: Vec<Run>,
    cp_last: Option<f64>,
    cp_k: i64,
    cp_moved: f64,
    stop_t: Option<i64>,
    stopped: bool,
    cash: Option<f64>,
    peak: Option<f64>,
    vg_last: Option<f64>,
    vg_fast: Option<f64>,
    vg_slow: Option<f64>,
    vg_n: i64,
    jump_last: Option<f64>,
    jump_age: i64,
    jump_sign: i64,
    jump_n: i64,
    jump_rev: i64,
    copy_age: i64,
    cp_low: Option<f64>,
    cp_high: Option<f64>,
    cp_ticks: i64,
    cp_fair: Option<f64>,
    cp_bid: Option<i64>,
    cp_ask: Option<i64>,
    cost: Option<f64>,
    delta: Option<f64>,
    offset: Option<f64>,
}

/// changepoint_level's run: [chance, mean, variance, first block].
#[derive(Clone, Copy, PartialEq, PartialOrd)]
struct Run(f64, f64, f64, i64);

// ------------------------------------------------------------------------------ STRATEGY

/// The book as STRATEGY sees it: [price, volume] levels, best first. take and clear use them up.
#[derive(Clone)]
struct Levels {
    bids: Vec<[i64; 2]>,
    asks: Vec<[i64; 2]>,
}

impl Levels {
    fn read(book: &Book) -> Levels {
        Levels { bids: book.bids.iter().map(|&(p, v)| [p, v]).collect(), asks: book.asks.iter().map(|&(p, v)| [p, v]).collect() }
    }
}

struct Plan {
    position: i64,
    limit: i64,
    bought: i64,
    sold: i64,
    takes: Vec<(Price, i64)>,
    quotes: Vec<(Price, i64)>,
    fair: Option<f64>,
    target: i64,
    legs: Vec<(Option<usize>, f64)>, // a product's index (None: not on the day) -> the basket's wish for it
}

impl Plan {
    fn new(position: i64, limit: i64) -> Plan {
        Plan { position, limit, bought: 0, sold: 0, takes: Vec::new(), quotes: Vec::new(), fair: None, target: 0, legs: Vec::new() }
    }

    fn net(&self) -> i64 {
        self.position + self.bought - self.sold
    }

    fn buy_room(&self) -> i64 {
        self.limit - self.position - self.bought
    }

    fn sell_room(&self) -> i64 {
        self.limit + self.position - self.sold
    }

    fn buy(&mut self, price: Price, quantity: i64, quote: bool) -> i64 {
        let quantity = quantity.min(self.buy_room());
        if quantity > 0 {
            if quote { &mut self.quotes } else { &mut self.takes }.push((price, quantity));
            self.bought += quantity;
        }
        quantity.max(0)
    }

    fn sell(&mut self, price: Price, quantity: i64, quote: bool) -> i64 {
        let quantity = quantity.min(self.sell_room());
        if quantity > 0 {
            if quote { &mut self.quotes } else { &mut self.takes }.push((price, -quantity));
            self.sold += quantity;
        }
        quantity.max(0)
    }
}

/// What a product's strategy sees of the others (Python's Market).
struct Market<'a> {
    books: &'a [Option<Book>],
    trades: &'a [(Name, Name, i64, Price)], // this product's: (buyer, seller, quantity, price)
    fills: &'a [(Price, i64)],       // this product's own fills
    timestamp: i64,
    plans: &'a [Option<Plan>],
    plan_order: &'a [usize],
    weights: &'a [f64], // copy's weight per trader name, for this product
}

fn trade_product(product: usize, book: &Book, position: i64, p: &P, memory: &mut Memory, market: &Market) -> Plan {
    let mut plan = Plan::new(position, p.limit);
    let fair = if p.smile.is_some() { smile_fair(book, p, memory, market) } else { fair_value(book, p, memory) };
    let Some(mut fair) = fair else { return plan };
    let spread = if !book.bids.is_empty() && !book.asks.is_empty() { book.asks[0].0 - book.bids[0].0 } else { 0 };
    let mut e = Eff {
        target: p.target,
        take_buy: p.take_edge_buy.unwrap_or(p.take_edge),
        take_sell: p.take_edge_sell.unwrap_or(p.take_edge),
        make_buy: p.make_edge_buy.unwrap_or(p.make_edge),
        make_sell: p.make_edge_sell.unwrap_or(p.make_edge),
        clear_edge: p.clear_edge,
        make_size: p.make_size,
        reduce_only: p.reduce_only,
        pull: 0,
    };
    let inf = f64::INFINITY;
    if p.flatten_from.is_some_and(|from| market.timestamp as f64 >= from) {
        let edge = p.flatten_edge.unwrap_or(spread as f64);
        e = match p.flatten_keep {
            Some(keep) if position.abs() as f64 <= keep => Eff {
                target: position, take_buy: inf, take_sell: inf, make_buy: e.make_buy + p.flatten_widen, make_sell: e.make_sell + p.flatten_widen,
                clear_edge: -inf, reduce_only: false, ..e
            },
            keep => Eff { target: keep.map_or(0, |k| k.copysign(position as f64) as i64), take_buy: inf, take_sell: inf, clear_edge: edge, reduce_only: true, ..e },
        };
    } else if p.stop_loss.is_some() && loss_stop(fair, position, market.fills, market.timestamp, p, memory) {
        e = Eff { target: 0, take_buy: inf, take_sell: inf, make_size: Some(0), clear_edge: p.stop_edge.unwrap_or(spread as f64), ..e };
    } else if p.vol_guard.is_some() && regime_guard(fair, p, memory) {
        // plain market making toward the static target
    } else if p.basket.is_some() {
        e.target = basket_target(fair, p, memory, market, &mut plan);
    } else if p.level != Level::Off {
        e.target = level_target(fair, p, memory);
    } else if p.copy.is_some() || p.copy_sizes.is_some() {
        let target = copy_target(market.trades, market.weights, p, memory, fair, book);
        e = Eff { target, clear_edge: if target != 0 { p.copy_edge } else { p.clear_edge }, ..e };
    } else if p.jump_min.is_some() {
        let target = jump_target(fair, p, memory);
        e = Eff { target, clear_edge: if target != 0 { p.jump_edge } else { p.clear_edge }, ..e };
    } else if p.follow.is_some() {
        let underlying = p.follow_id.and_then(|k| market.plans[k].as_ref());
        e.target = follow_target(book, fair, p, memory, underlying);
    } else if p.hedge {
        e.target = hedge_target(product, p, market);
    }
    if p.smile.is_some() && p.hedge_ratio != 0.0 {
        plan.legs = vec![(p.underlying_id, -p.hedge_ratio * memory.delta.unwrap_or(0.0) * position as f64)];
    }
    plan.fair = Some(fair);
    plan.target = e.target;
    let (trend, recent) = moves(fair, p, memory);
    if p.imbalance != 0.0 && !book.bids.is_empty() && !book.asks.is_empty() {
        fair += p.imbalance * imbalance(book);
    }
    if p.lin_rho3 != 0.0 && !book.bids.is_empty() && !book.asks.is_empty() {
        fair += p.lin_rho3 * depth_imbalance(book, 3);
    }
    fair += p.lin_momentum * trend;
    if p.gate_move.is_some_and(|gate| recent.abs() >= gate) {
        e.pull = if recent > 0.0 { 1 } else { -1 };
    }
    let mut levels = Levels::read(book); // take and clear use up its levels
    take(&mut levels, fair, p, &e, &mut plan);
    clear(&mut levels, fair, p, &e, &mut plan);
    make(&levels, fair, p, &e, &mut plan);
    plan
}

fn fair_value(book: &Book, p: &P, memory: &mut Memory) -> Option<f64> {
    if p.fair == Fair::Fixed {
        if let (Some(guard), Some(fixed)) = (p.fixed_guard, p.fixed_fair) {
            let market = mid(sized(&book.bids, p.wall_size), sized(&book.asks, p.wall_size));
            if let Some(market) = market {
                if (market - fixed).abs() > guard {
                    return Some(market);
                }
            }
        }
        return p.fixed_fair;
    }
    let previous = memory.fair;
    let Some(mut fair) = price(book, p) else { return previous };
    if p.fair == Fair::HysteresisMid {
        if fair == fair.floor() {
            // an even spread puts the mid on a tick: the half tick on the side of the last value
            fair += if memory.hysteresis.is_some_and(|last| last > fair) { 0.5 } else { -0.5 };
        }
        memory.hysteresis = Some(fair);
    }
    if let Some(previous) = previous {
        if p.smoothing != 0.0 {
            fair = p.smoothing * previous + (1.0 - p.smoothing) * fair;
        }
    }
    memory.fair = Some(fair);
    Some(fair)
}

fn price(book: &Book, p: &P) -> Option<f64> {
    match p.fair {
        Fair::Fixed => p.fixed_fair,
        Fair::Mid | Fair::HysteresisMid => mid(book.bids.first(), book.asks.first()),
        Fair::WallMid => mid(wall(&book.bids), wall(&book.asks)),
        Fair::OuterMid => mid(book.bids.last(), book.asks.last()),
        Fair::SizedMid => mid(sized(&book.bids, p.wall_size), sized(&book.asks, p.wall_size)),
        Fair::WeightedMid => {
            let (bid, ask) = (book.bids.first()?, book.asks.first()?);
            let share = bid.1 as f64 / (bid.1 + ask.1) as f64;
            Some(share * ask.0 as f64 + (1.0 - share) * bid.0 as f64)
        }
    }
}

fn imbalance(book: &Book) -> f64 {
    let (bid, ask) = (book.bids[0].1, book.asks[0].1);
    (bid - ask) as f64 / (bid + ask) as f64
}

fn depth_imbalance(book: &Book, depth: usize) -> f64 {
    let bid: i64 = book.bids.iter().take(depth).map(|l| l.1).sum();
    let ask: i64 = book.asks.iter().take(depth).map(|l| l.1).sum();
    (bid - ask) as f64 / (bid + ask) as f64
}

/// The fair's move over lin_window and over gate_window ticks (0 until it has that many); memory keeps
/// the last fairs, only while either is on.
fn moves(fair: f64, p: &P, memory: &mut Memory) -> (f64, f64) {
    let lin = if p.lin_momentum != 0.0 { p.lin_window.max(0) as usize } else { 0 };
    let gate = if p.gate_move.is_some() { p.gate_window.max(0) as usize } else { 0 };
    if lin == 0 && gate == 0 {
        return (0.0, 0.0);
    }
    memory.trail.push(fair);
    let keep = lin.max(gate) + 1;
    if memory.trail.len() > keep {
        memory.trail.drain(..memory.trail.len() - keep);
    }
    let n = memory.trail.len();
    let moved = |k: usize| if k != 0 && n > k { fair - memory.trail[n - k - 1] } else { 0.0 };
    (moved(lin), moved(gate))
}

fn mid(bid: Option<&(Price, i64)>, ask: Option<&(Price, i64)>) -> Option<f64> {
    Some((bid?.0 + ask?.0) as f64 / 2.0)
}

/// The level with the most volume (the first of equals, as Python's max).
fn wall(levels: &[(Price, i64)]) -> Option<&(Price, i64)> {
    let mut best = levels.first()?;
    for level in &levels[1..] {
        if level.1 > best.1 {
            best = level;
        }
    }
    Some(best)
}

/// The first level from the top with at least `size`, else the best level.
fn sized(levels: &[(Price, i64)], size: f64) -> Option<&(Price, i64)> {
    levels.iter().find(|l| l.1 as f64 >= size).or(levels.first())
}

fn level_target(fair: f64, p: &P, memory: &mut Memory) -> i64 {
    let gap = fair - estimate_level(fair, p, memory);
    let mut held = memory.held;
    if let Some(guard) = p.level_guard {
        if gap.abs() > guard * p.level_band {
            memory.broken = true;
        } else if gap.abs() < p.level_band {
            memory.broken = false;
        }
    }
    if p.cpd_hazard.is_some() && p.cpd_action == CpdAction::Drop && memory.cp_moved > p.cpd_threshold {
        memory.broken = true;
    }
    if memory.broken {
        held = 0;
    } else if gap >= p.level_band {
        held = -p.limit;
    } else if gap <= -p.level_band {
        held = p.limit;
    } else if let Some(exit) = p.level_exit {
        if (held < 0 && gap <= exit) || (held > 0 && gap >= -exit) {
            held = 0;
        }
    }
    memory.held = held;
    held
}

fn loss_stop(fair: f64, position: i64, fills: &[(Price, i64)], timestamp: i64, p: &P, memory: &mut Memory) -> bool {
    if timestamp < memory.stop_t.unwrap_or(-1) {
        memory.stopped = false;
        memory.cash = Some(-position as f64 * fair);
        memory.peak = Some(0.0);
    }
    memory.stop_t = Some(timestamp);
    let spent: i64 = fills.iter().map(|&(price, quantity)| price * quantity).sum();
    let cash = memory.cash.unwrap_or(0.0) - spent as f64;
    memory.cash = Some(cash);
    let pnl = cash + position as f64 * fair;
    let peak = memory.peak.unwrap_or(0.0);
    let peak = if pnl > peak { pnl } else { peak };
    memory.peak = Some(peak);
    if peak - pnl > p.stop_loss.unwrap() {
        memory.stopped = true;
    }
    memory.stopped
}

fn regime_guard(fair: f64, p: &P, memory: &mut Memory) -> bool {
    let last = memory.vg_last;
    memory.vg_last = Some(fair);
    let Some(last) = last else { return false };
    let change = sq(fair - last);
    let fast = 0.95 * memory.vg_fast.unwrap_or(change) + 0.05 * change;
    let slow = 0.999 * memory.vg_slow.unwrap_or(change) + 0.001 * change;
    memory.vg_fast = Some(fast);
    memory.vg_slow = Some(slow);
    memory.vg_n += 1;
    memory.vg_n >= 200 && fast > sq(p.vol_guard.unwrap()) * if 1e-9 > slow { 1e-9 } else { slow }
}

fn estimate_level(fair: f64, p: &P, memory: &mut Memory) -> f64 {
    memory.level_sum += fair;
    memory.level_n += 1;
    let level = match p.level {
        Level::Day => return memory.level_sum / memory.level_n as f64,
        Level::At(level) => level,
        Level::Off => unreachable!("level_target runs only with a level"),
    };
    if p.cpd_hazard.is_some() {
        return changepoint_level(fair, level, p, memory);
    }
    match p.level_weight {
        None => level,
        Some(weight) => (level * weight + memory.level_sum) / (weight + memory.level_n as f64),
    }
}

fn changepoint_level(fair: f64, level: f64, p: &P, memory: &mut Memory) -> f64 {
    memory.cp_sum += fair;
    memory.cp_n += 1;
    if memory.cp_n < p.cpd_block {
        return if p.cpd_action == CpdAction::Level { memory.cp_level.unwrap_or(level) } else { level };
    }
    let x = memory.cp_sum / memory.cp_n as f64;
    memory.cp_sum = 0.0;
    memory.cp_n = 0;
    let (block, theta, sd) = (p.cpd_block as f64, p.cpd_reversion, p.cpd_sd);
    let phi = (-theta * block).exp();
    let stationary = sd * sd / (2.0 * theta);
    let noise = stationary * (1.0 - phi * phi) / sq(1.0 - phi);
    let mut runs = if memory.cp_runs.is_empty() { vec![Run(1.0, level, stationary / 4.0, 0)] } else { std::mem::take(&mut memory.cp_runs) };
    let last = memory.cp_last;
    memory.cp_last = Some(x);
    memory.cp_k += 1;
    let k = memory.cp_k;
    if let Some(last) = last {
        let z = (x - phi * last) / (1.0 - phi);
        let hazard = { let h = block / p.cpd_hazard.unwrap(); if 1.0 < h { 1.0 } else { h } };
        let mut grown = Vec::with_capacity(runs.len() + 1);
        let mut shifted = 0.0;
        for &Run(chance, mean, var, first) in &runs {
            let spread = var + noise;
            let likelihood = (-sq(z - mean) / (2.0 * spread)).exp() / spread.sqrt();
            grown.push(Run(chance * likelihood * (1.0 - hazard), (mean / var + z / noise) / (1.0 / var + 1.0 / noise), 1.0 / (1.0 / var + 1.0 / noise), first));
            shifted += chance * likelihood * hazard;
        }
        let mut all = vec![Run(shifted, x, stationary, k)];
        all.extend(grown);
        let total = { let t = all.iter().fold(0.0, |s, r| s + r.0); if t != 0.0 { t } else { 1.0 } };
        runs = all.into_iter().map(|Run(c, m, v, f)| Run(c / total, m, v, f)).filter(|r| r.0 > 1e-6).collect();
        runs.sort_by(|a, b| b.partial_cmp(a).unwrap());
        runs.truncate(40);
    }
    memory.cp_moved = 1.0 - runs.iter().filter(|r| r.3 == 0).fold(0.0, |s, r| s + r.0);
    let level_now = runs.iter().fold(0.0, |s, r| s + r.0 * r.1) / runs.iter().fold(0.0, |s, r| s + r.0);
    memory.cp_level = Some(level_now);
    memory.cp_runs = runs;
    if p.cpd_action == CpdAction::Level { level_now } else { level }
}

fn jump_target(fair: f64, p: &P, memory: &mut Memory) -> i64 {
    let last = memory.jump_last;
    memory.jump_last = Some(fair);
    let (mut held, mut age) = (memory.held, memory.jump_age + 1);
    match last {
        Some(last) if (fair - last).abs() >= p.jump_min.unwrap() => {
            let sign = if fair > last { 1 } else { -1 };
            if memory.jump_sign != 0 {
                memory.jump_n += 1;
                memory.jump_rev += (sign != memory.jump_sign) as i64;
            }
            memory.jump_sign = sign;
            let (n, reversed) = (memory.jump_n, memory.jump_rev);
            held = if n as f64 >= p.jump_seen && reversed as f64 >= p.jump_share * n as f64 { -sign * p.limit } else { 0 };
            age = 0;
        }
        _ => {
            if p.jump_hold.is_some_and(|hold| age as f64 >= hold) {
                held = 0;
            }
        }
    }
    memory.held = held;
    memory.jump_age = age;
    held
}

fn copy_target(trades: &[(Name, Name, i64, Price)], weights: &[f64], p: &P, memory: &mut Memory, fair: f64, book: &Book) -> i64 {
    let mut signal = trades.iter().fold(0.0, |s, &(buyer, seller, _, _)| s + (weights[buyer as usize] - weights[seller as usize]));
    if p.copy_sizes.is_some() {
        signal += informed_signal(trades, fair, book, p, memory) as f64;
    }
    let (mut held, mut age) = (memory.held, memory.copy_age + 1);
    if signal != 0.0 {
        let capped = if signal < 1.0 { signal } else { 1.0 };
        let capped = if capped > -1.0 { capped } else { -1.0 };
        held = round(capped * p.limit as f64);
        age = 0;
    } else if p.copy_hold.is_some_and(|hold| age as f64 >= hold) {
        held = 0;
    }
    memory.held = held;
    memory.copy_age = age;
    held
}

/// +1 for each trade of a copy_sizes size that bought at the day's running low of the fair, -1 for each that
/// sold at its high; its side from the book the bot saw before it printed.
fn informed_signal(trades: &[(Name, Name, i64, Price)], fair: f64, book: &Book, p: &P, memory: &mut Memory) -> i64 {
    let sizes = p.copy_sizes.as_deref().unwrap_or(&[]);
    let mut signal = 0;
    let warm = memory.cp_ticks >= p.copy_warmup;
    if let (true, Some(bid), Some(ask), Some(low), Some(high), Some(last)) = (warm, memory.cp_bid, memory.cp_ask, memory.cp_low, memory.cp_high, memory.cp_fair) {
        for &(_, _, quantity, price) in trades {
            if sizes.contains(&quantity) {
                let buying = price >= ask || (price > bid && price as f64 >= (bid + ask) as f64 / 2.0);
                if buying && last <= low {
                    signal += 1;
                } else if !buying && last >= high {
                    signal -= 1;
                }
            }
        }
    }
    if let Some(last) = memory.cp_fair {
        // the extremes before the latest fair
        memory.cp_low = Some(memory.cp_low.map_or(last, |low| low.min(last)));
        memory.cp_high = Some(memory.cp_high.map_or(last, |high| high.max(last)));
    }
    memory.cp_fair = Some(fair);
    memory.cp_ticks += 1;
    if let (Some(bid), Some(ask)) = (book.bids.first(), book.asks.first()) {
        memory.cp_bid = Some(bid.0);
        memory.cp_ask = Some(ask.0);
    }
    signal
}

fn follow_target(book: &Book, fair: f64, p: &P, memory: &mut Memory, underlying: Option<&Plan>) -> i64 {
    let Some(underlying) = underlying else { return memory.held };
    let Some(s) = underlying.fair else { return memory.held };
    if book.bids.is_empty() || book.asks.is_empty() {
        return memory.held;
    }
    let k = p.strike;
    let delta = call_delta(s, k, implied_variance(fair, s, k));
    let half_spread = (book.asks[0].0 - book.bids[0].0) as f64 / 2.0;
    let cost = if delta > 1e-6 { half_spread / delta } else { 1e9 };
    let cost = match memory.cost {
        None => cost,
        Some(last) => 0.95 * last + 0.05 * cost,
    };
    memory.cost = Some(cost);
    let held = if cost > p.max_cost_per_delta { 0 } else { round(underlying.target as f64 / underlying.limit as f64 * p.limit as f64) };
    memory.held = held;
    held
}

fn call_price(s: f64, k: f64, w: f64) -> f64 {
    if w <= 0.0 {
        let intrinsic = s - k;
        return if 0.0 > intrinsic { 0.0 } else { intrinsic };
    }
    let d1 = ((s / k).ln() + w / 2.0) / w.sqrt();
    s * cdf(d1) - k * cdf(d1 - w.sqrt())
}

fn call_delta(s: f64, k: f64, w: f64) -> f64 {
    if w <= 0.0 {
        return if s > k { 1.0 } else { 0.0 };
    }
    cdf(((s / k).ln() + w / 2.0) / w.sqrt())
}

fn implied_variance(price: f64, s: f64, k: f64) -> f64 {
    let intrinsic = s - k;
    if price <= (if 0.0 > intrinsic { 0.0 } else { intrinsic }) {
        return 0.0;
    }
    let (mut lo, mut hi) = (0.0, 4.0);
    for _ in 0..50 {
        let mid_w = (lo + hi) / 2.0;
        if call_price(s, k, mid_w) < price {
            lo = mid_w;
        } else {
            hi = mid_w;
        }
    }
    (lo + hi) / 2.0
}

fn smile_fair(book: &Book, p: &P, memory: &mut Memory, market: &Market) -> Option<f64> {
    let underlying = p.underlying_id.and_then(|k| market.books[k].as_ref());
    let s = underlying.and_then(|u| price(u, p));
    let own = price(book, p);
    let (Some(s), Some(own)) = (s, own) else { return memory.fair };
    let k = p.strike;
    let t = { let left = p.expiry - market.timestamp as f64 / p.day_length; if 1e-6 > left { 1e-6 } else { left } } / 365.0;
    let (a, b, c) = p.smile.unwrap();
    let m = (k / s).ln() / t.sqrt();
    let v = a * m * m + b * m + c;
    let w = sq(if 0.0 > v { 0.0 } else { v }) * t;
    let model = call_price(s, k, w);
    memory.delta = Some(call_delta(s, k, w));
    let offset = memory.offset.unwrap_or(own - model);
    memory.offset = Some(offset + 2.0 / (p.smile_window + 1.0) * (own - model - offset));
    memory.fair = Some(model + offset);
    memory.fair
}

fn basket_target(fair: f64, p: &P, memory: &mut Memory, market: &Market, plan: &mut Plan) -> i64 {
    let basket = p.basket.as_ref().unwrap();
    let legs: Option<Vec<f64>> = p.basket_ids.iter().map(|&id| id.and_then(|k| market.books[k].as_ref()).and_then(|b| price(b, p))).collect();
    let target = match legs {
        None => memory.held,
        Some(legs) => {
            let spread = fair - basket.iter().zip(&legs).fold(0.0, |s, ((_, weight), leg)| s + weight * leg);
            level_target(spread, p, memory)
        }
    };
    plan.legs = basket.iter().zip(&p.basket_ids).map(|((_, weight), &id)| (id, -weight * p.hedge_ratio * target as f64)).collect();
    target
}

fn hedge_target(product: usize, p: &P, market: &Market) -> i64 {
    let mut wanted = 0.0;
    for &k in market.plan_order {
        let plan = market.plans[k].as_ref().unwrap();
        wanted += plan.legs.iter().find(|(id, _)| *id == Some(product)).map_or(0.0, |(_, v)| *v);
    }
    round(wanted).clamp(-p.limit, p.limit)
}

fn take(book: &mut Levels, fair: f64, p: &P, e: &Eff, plan: &mut Plan) {
    for level in book.asks.iter_mut() {
        if level[0] as f64 > fair - e.take_buy {
            break;
        }
        let quantity = crossable(level[1], p, plan);
        level[1] -= plan.buy(level[0], quantity, false);
    }
    for level in book.bids.iter_mut() {
        if (level[0] as f64) < fair + e.take_sell {
            break;
        }
        let quantity = crossable(level[1], p, plan);
        level[1] -= plan.sell(level[0], quantity, false);
    }
}

/// What cross_max leaves of a level's volume to cross this tick.
fn crossable(volume: i64, p: &P, plan: &Plan) -> i64 {
    match p.cross_max {
        None => volume,
        Some(cap) => volume.min((cap - plan.takes.iter().map(|t| t.1.abs()).sum::<i64>()).max(0)),
    }
}

fn clear(book: &mut Levels, fair: f64, p: &P, e: &Eff, plan: &mut Plan) {
    let (target, excess) = (e.target, p.cross_excess.unwrap_or(0));
    if plan.net() > target + excess {
        for level in book.bids.iter_mut() {
            if (level[0] as f64) < fair - e.clear_edge || plan.net() <= target + excess {
                break;
            }
            let quantity = crossable(level[1].min(plan.net() - target - excess), p, plan);
            level[1] -= plan.sell(level[0], quantity, false);
        }
    } else if plan.net() < target - excess {
        for level in book.asks.iter_mut() {
            if level[0] as f64 > fair + e.clear_edge || plan.net() >= target - excess {
                break;
            }
            let quantity = crossable(level[1].min(target - excess - plan.net()), p, plan);
            level[1] -= plan.buy(level[0], quantity, false);
        }
    }
}

fn make(book: &Levels, fair: f64, p: &P, e: &Eff, plan: &mut Plan) {
    let best_bid = book.bids.iter().find(|l| l[1] > 0).map(|l| l[0]);
    let best_ask = book.asks.iter().find(|l| l[1] > 0).map(|l| l[0]);

    let mut bid = (fair - e.make_buy).floor() as i64;
    let mut ask = (fair + e.make_sell).ceil() as i64;
    if let (Some(best), Some(inside)) = (best_bid, p.make_inside) {
        bid = bid.min(best + inside);
    }
    if let (Some(best), Some(inside)) = (best_ask, p.make_inside) {
        ask = ask.max(best - inside);
    }

    let shift = round(p.skew * (plan.net() - e.target) as f64 / plan.limit as f64);
    bid -= shift;
    ask -= shift;
    if let Some(best) = best_ask {
        bid = bid.min(best - 1);
    }
    if let Some(best) = best_bid {
        ask = ask.max(best + 1);
    }
    if bid >= ask {
        if plan.net() >= e.target {
            bid = ask - 1;
        } else {
            ask = bid + 1;
        }
    }
    if let (Some(join), Some(best_b), Some(best_a)) = (p.join_min, best_bid, best_ask) {
        let volume = |levels: &[[i64; 2]], price: i64| levels.iter().find(|l| l[0] == price).map_or(0, |l| l[1]) as f64;
        let (bids, asks) = (volume(&book.bids, best_b), volume(&book.asks, best_a));
        if bid == best_b && (bids < join || asks > p.join_ratio * bids) {
            bid -= 1;
        }
        if ask == best_a && (asks < join || bids > p.join_ratio * asks) {
            ask += 1;
        }
    }

    let gap = p.size_skew * (plan.net() - e.target) as f64 / plan.limit as f64;
    let mut buy = scaled(e.make_size.unwrap_or(plan.buy_room()), 1.0 - gap);
    let mut sell = scaled(e.make_size.unwrap_or(plan.sell_room()), 1.0 + gap);
    if e.reduce_only {
        buy = buy.min((e.target - plan.net()).max(0));
        sell = sell.min((plan.net() - e.target).max(0));
    }
    if p.take_reserve != 0 {
        buy = buy.min((plan.buy_room() - p.take_reserve).max(0));
        sell = sell.min((plan.sell_room() - p.take_reserve).max(0));
    }
    if e.pull == 1 {
        sell = 0; // the fair just rose: don't sell into it
    } else if e.pull == -1 {
        buy = 0;
    }
    let (levels, step) = (p.make_levels, p.make_step);
    for k in 0..levels {
        // the first price gets the remainder of an uneven split, as Python's // and %
        plan.buy(bid - k * step, buy.div_euclid(levels) + if k == 0 { buy.rem_euclid(levels) } else { 0 }, true);
        plan.sell(ask + k * step, sell.div_euclid(levels) + if k == 0 { sell.rem_euclid(levels) } else { 0 }, true);
    }
}

fn scaled(size: i64, factor: f64) -> i64 {
    (size as f64 * if 0.0 > factor { 0.0 } else { factor }).trunc() as i64
}

// ------------------------------------------------------------------------------ EXECUTION

/// Pushes the plan's cancels and new orders: resting holds (id, price, signed quantity left), oldest first.
fn execute(product: usize, plan: &Plan, resting: &[(u64, Price, i64)], out: &mut Vec<Action>) {
    let mut wanted: Vec<((bool, Price), i64)> = Vec::with_capacity(2);
    for &(price, quantity) in &plan.quotes {
        let key = (quantity > 0, price);
        match wanted.iter_mut().find(|(k, _)| *k == key) {
            Some((_, v)) => *v += quantity,
            None => wanted.push((key, quantity)),
        }
    }
    for &(id, price, quantity) in resting {
        let key = (quantity > 0, price);
        match wanted.iter_mut().find(|(k, _)| *k == key) {
            Some((_, v)) if quantity.abs() <= v.abs() => *v -= quantity,
            _ => out.push(Action::Cancel(id)),
        }
    }
    for &(price, quantity) in &plan.takes {
        out.push(Action::Order(Order { product, price, quantity, ioc: true }));
    }
    for &((_, price), quantity) in &wanted {
        if quantity != 0 {
            out.push(Action::Order(Order { product, price, quantity, ioc: false }));
        }
    }
}

// ------------------------------------------------------------------------------ ADAPTER

#[path = "drill/template.rs"]
mod drill;
use drill::Drill;

/// How a template file's ADAPTER presents the engine's tick to STRATEGY and sends its plan back: the
/// choices each format's template makes (rust/twins.json, a twin's `adapter`). Prosperity's template
/// and the drill's are the two presets; a new format's template, written by the same conventions,
/// is a twin by naming its choices (`Adapter::read`), checked by `experiments.rust_bench --twin`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Adapter {
    pub units: bool,          // the engine's prices are in Day.info's unit: STRATEGY sees each product's ticks (the drill's)
    pub names: bool,          // the market's trades name their traders, so `copy` can read them (Prosperity's)
    pub own_trades: bool,     // our fills reach STRATEGY as Prosperity's own_trades: among the trades, signed by buyer == us
    pub exchange_limit: bool, // each product's limit is the exchange's (Day.limits), not PARAMS' (the drill's)
    pub exchange_order: bool, // products in the exchange's order (Day.limits'), those with a level; else the tick's (the drill's)
    pub sorted_resting: bool, // resting orders sorted by (timestamp, id); else as the engine lists them, oldest first (Prosperity's)
}

impl Adapter {
    pub const PROSPERITY: Adapter =
        Adapter { units: false, names: true, own_trades: true, exchange_limit: false, exchange_order: false, sorted_resting: true };
    pub const DRILL: Adapter =
        Adapter { units: true, names: false, own_trades: false, exchange_limit: true, exchange_order: true, sorted_resting: false };

    /// "prosperity", "drill", or {choice: bool, ...}, the choices left out taken from Prosperity's.
    pub fn read(value: &Value) -> Result<Adapter, String> {
        match value {
            Value::Str(name) if name == "prosperity" => Ok(Adapter::PROSPERITY),
            Value::Str(name) if name == "drill" => Ok(Adapter::DRILL),
            Value::Object(choices) => {
                let mut a = Adapter::PROSPERITY;
                for (key, v) in choices {
                    let on = match v {
                        Value::Bool(b) => *b,
                        _ => return Err(format!("adapter choice {key} must be true or false")),
                    };
                    match key.as_str() {
                        "units" => a.units = on,
                        "names" => a.names = on,
                        "own_trades" => a.own_trades = on,
                        "exchange_limit" => a.exchange_limit = on,
                        "exchange_order" => a.exchange_order = on,
                        "sorted_resting" => a.sorted_resting = on,
                        other => return Err(format!("no adapter choice {other:?} (units, names, own_trades, exchange_limit, exchange_order, sorted_resting)")),
                    }
                }
                Ok(a)
            }
            _ => Err("an adapter is \"prosperity\", \"drill\" or an object of choices".to_string()),
        }
    }
}

pub struct Template {
    adapter: Adapter,
    units: Drill, // with adapter.units: each product's tick and unit, and its book in ticks
    settings: Vec<(String, P, bool)>, // PARAMS: product, its merged settings, and whether it depends on another (_depends)
    // Per product of the day, set by begin_day.
    params: Vec<Option<P>>,
    depends: Vec<bool>,
    weights: Vec<Vec<f64>>, // copy's weight per trader name, per product
    memory: Vec<Memory>,
    // Buffers reused tick to tick.
    order: Vec<usize>,
    trades: Vec<Vec<(Name, Name, i64, Price)>>,
    fills: Vec<Vec<(Price, i64)>>,
    plans: Vec<Option<Plan>>,
    plan_order: Vec<usize>,
    resting: Vec<(i64, u64, Price, i64)>,
    us: Name,
    symbols: Vec<usize>, // the day's products in its limits' order (the drill's api.symbols())
}

/// `params_for`'s check that each PARAMS entry names its limit, for an ADAPTER that takes the limit
/// from PARAMS (Prosperity's): DEFAULTS' is a placeholder.
pub fn require_limits(globals: &Value) -> Result<(), String> {
    let params = globals.get("PARAMS").and_then(Value::as_object).ok_or("the template's PARAMS must be a dict")?;
    for (product, own) in params {
        if !own.as_object().is_some_and(|own| own.iter().any(|(k, _)| k == "limit")) {
            return Err(format!("no limit for {product}: set the competition's in PARAMS"));
        }
    }
    Ok(())
}

impl Template {
    /// From the Python file's globals (python/arena/rust.py `bot_globals`): DEFAULTS and PARAMS.
    pub fn from_globals(globals: &Value) -> Result<Template, String> {
        let defaults = globals.get("DEFAULTS").and_then(Value::as_object).ok_or("the template's DEFAULTS must be a dict")?.to_vec();
        let params = globals.get("PARAMS").and_then(Value::as_object).ok_or("the template's PARAMS must be a dict")?;
        let mut settings = Vec::new();
        for (product, own) in params {
            let own = own.as_object().ok_or_else(|| format!("PARAMS[{product}] must be a dict"))?;
            let mut unknown: Vec<&str> = own.iter().map(|(k, _)| k.as_str()).filter(|k| !defaults.iter().any(|(d, _)| d == k)).collect();
            if !unknown.is_empty() {
                unknown.sort_unstable();
                return Err(format!("unknown params for {product}: {}", unknown.join(", ")));
            }
            let merged: Vec<(String, Value)> = defaults.iter().chain(own).cloned().collect();
            let p = P::read(product, &merged)?;
            let depends = own.iter().any(|(k, v)| (k == "follow" && !v.is_null()) || (k == "hedge" && v.truthy()));
            settings.push((product.clone(), p, depends));
        }
        Ok(Template {
            adapter: Adapter::PROSPERITY,
            units: Drill::default(),
            settings,
            params: Vec::new(),
            depends: Vec::new(),
            weights: Vec::new(),
            memory: Vec::new(),
            order: Vec::new(),
            trades: Vec::new(),
            fills: Vec::new(),
            plans: Vec::new(),
            plan_order: Vec::new(),
            resting: Vec::new(),
            us: Name::MAX,
            symbols: Vec::new(),
        })
    }

    /// The same settings behind another ADAPTER.
    pub fn with_adapter(self, adapter: Adapter) -> Template {
        Template { adapter, ..self }
    }
}

/// How Prosperity names us in own_trades.
const US: &str = "SUBMISSION";

impl Bot for Template {
    fn memory(&self, day: &Day) -> Option<String> {
        let mut out = String::from("{");
        for (k, memory) in self.memory.iter().enumerate() {
            if memory.stopped {
                if out.len() > 1 {
                    out.push_str(", ");
                }
                crate::support::json::string(&mut out, &day.products[k]);
                out.push_str(": {\"stopped\": true}");
            }
        }
        out.push('}');
        Some(out)
    }

    fn begin_day(&mut self, day: &Day, names: &[String]) {
        let n = day.products.len();
        self.params = vec![None; n];
        self.depends = vec![false; n];
        for (product, p, depends) in &self.settings {
            if let Some(k) = day.product(product) {
                let mut p = p.clone();
                p.follow_id = p.follow.as_deref().and_then(|f| day.product(f));
                p.underlying_id = p.underlying.as_deref().and_then(|u| day.product(u));
                p.basket_ids = p.basket.iter().flatten().map(|(leg, _)| day.product(leg)).collect();
                self.params[k] = Some(p);
                self.depends[k] = *depends;
            }
        }
        // Names: the engine's table, plus SUBMISSION for our own side of our fills.
        self.us = names.iter().position(|s| s == US).unwrap_or(names.len()) as Name;
        let all = names.len() + 1;
        self.weights = (0..n)
            .map(|k| {
                let copy = self.params[k].as_ref().and_then(|p| p.copy.as_ref());
                (0..all)
                    .map(|i| {
                        let name = names.get(i).map_or(US, String::as_str);
                        copy.and_then(|c| c.iter().rev().find(|(k, _)| k == name)).map_or(0.0, |(_, w)| *w)
                    })
                    .collect()
            })
            .collect();
        self.memory = vec![Memory::default(); n];
        self.trades = vec![Vec::new(); n];
        self.fills = vec![Vec::new(); n];
        self.plans = (0..n).map(|_| None).collect();
        if self.adapter.exchange_limit {
            // params_for: the limit comes from the exchange (the drill's api.max_position)
            for (k, p) in self.params.iter_mut().enumerate() {
                if let Some(p) = p {
                    p.limit = day.limits[k];
                }
            }
        }
        if self.adapter.units {
            let d = &mut self.units;
            d.tick = day.info.iter().map(|i| i.map_or(0.01, |(tick, _)| tick)).collect();
            d.unit = day.info.iter().map(|i| i.map_or(0.01, |(_, unit)| unit)).collect();
            d.books = vec![None; n];
        }
        self.symbols = day.limits_order.clone();
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], own_fills: &[Fill], market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        let a = self.adapter;
        let d = &mut self.units;
        if a.units {
            // read_book in ticks; a product with no level on either side has no book
            for (k, book) in tick.books.iter().enumerate() {
                d.books[k] = book.as_ref().filter(|b| !b.bids.is_empty() || !b.asks.is_empty()).map(|b| {
                    let side = |levels: &[(Price, i64)]| levels.iter().map(|&(price, volume)| (d.ticks(k, price), volume)).collect();
                    Book { bids: side(&b.bids), asks: side(&b.asks) }
                });
            }
        }
        let books: &[Option<Book>] = if a.units { &d.books } else { tick.books };
        // read_trades: (buyer, seller, quantity), named or not; read_fills: our fills as (price in ticks, signed quantity)
        for (k, list) in self.trades.iter_mut().enumerate() {
            list.clear();
            let price = |t: &MarketTrade| if a.units { d.ticks(k, t.price) } else { t.price };
            list.extend(market_trades[k].iter().map(|t| if a.names { (t.buyer, t.seller, t.quantity, price(t)) } else { (0, 0, t.quantity, price(t)) }));
            self.fills[k].clear();
        }
        for f in own_fills {
            let price = if a.units { d.ticks(f.product, f.price) } else { f.price };
            if a.own_trades {
                // our own fills with their counterparty among the trades; read_fills signs by `buyer == US`,
                // so a sale to a trader named SUBMISSION counts as a buy there too
                let (buyer, seller) = if f.quantity > 0 { (self.us, f.counterparty) } else { (f.counterparty, self.us) };
                self.trades[f.product].push((buyer, seller, f.quantity.abs(), price));
                self.fills[f.product].push((price, if buyer == self.us { f.quantity.abs() } else { -f.quantity.abs() }));
            } else {
                self.fills[f.product].push((price, f.quantity));
            }
        }
        // The products traded this tick, those that follow or hedge another last, so they see its plan.
        self.order.clear();
        if a.exchange_order {
            let has_level = |k: usize| books[k].as_ref().is_some_and(|b| !b.bids.is_empty() || !b.asks.is_empty());
            self.order.extend(self.symbols.iter().copied().filter(|&k| has_level(k)));
        } else {
            self.order.extend_from_slice(tick.order);
        }
        let depends = &self.depends;
        self.order.sort_by_key(|&k| depends[k]);
        for plan in self.plans.iter_mut() {
            *plan = None;
        }
        self.plan_order.clear();
        for i in 0..self.order.len() {
            let product = self.order[i];
            let Some(p) = self.params[product].as_ref() else { continue };
            let Some(book) = books[product].as_ref() else { continue };
            let market = Market {
                books,
                trades: &self.trades[product],
                fills: &self.fills[product],
                timestamp: tick.timestamp,
                plans: &self.plans,
                plan_order: &self.plan_order,
                weights: &self.weights[product],
            };
            let plan = trade_product(product, book, positions[product], p, &mut self.memory[product], &market);
            // read_resting: oldest first, by (timestamp, id), or as the engine lists them
            self.resting.clear();
            self.resting.extend(open_orders.iter().filter(|o| o.product == product).map(|o| {
                (o.timestamp, o.id, if a.units { d.ticks(product, o.price) } else { o.price }, o.quantity)
            }));
            if a.sorted_resting {
                self.resting.sort_unstable_by_key(|&(ts, id, _, _)| (ts, id));
            }
            let resting: Vec<(u64, Price, i64)> = self.resting.iter().map(|&(_, id, price, q)| (id, price, q)).collect();
            let start = out.len();
            execute(product, &plan, &resting, out);
            if a.units {
                for action in &mut out[start..] {
                    if let Action::Order(order) = action {
                        order.price = d.units(product, order.price);
                    }
                }
            }
            self.plans[product] = Some(plan);
            self.plan_order.push(product);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_adapter_is_a_preset_or_its_choices() {
        assert_eq!(Adapter::read(&Value::Str("drill".into())).unwrap(), Adapter::DRILL);
        let choices = Value::Object(vec![("units".into(), Value::Bool(true)), ("names".into(), Value::Bool(false))]);
        assert_eq!(Adapter::read(&choices).unwrap(), Adapter { units: true, names: false, ..Adapter::PROSPERITY });
        assert!(Adapter::read(&Value::Object(vec![("unit".into(), Value::Bool(true))])).is_err());
        assert!(Adapter::read(&Value::Str("qminers".into())).is_err());
    }
}
