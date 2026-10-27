//! python/arena/engine.py's `run_market`, ported function for function (the Python names are kept, so
//! each piece can be read next to its original). The rules are in that module's docstring: the
//! default mode (orders live one tick), resting mode with the back / prob / front queue models,
//! the fill ratio's seeded liquidity draws, several bots in one market with their arrival
//! shuffle, races and limit breaches, the marks and the limit penalty of another exchange's
//! scoring, the delay between a bot's decision and its orders reaching the exchange, and fees.
//! Everything a DayResult records per tick is recorded here too.
//!
//! Not ported: order tags (a format's own ids), the bot's exceptions, prints and step timings
//! (a Rust bot can't raise or print into the result), and `begin_day`'s per-product info.

use std::borrow::Cow;
use std::collections::VecDeque;

use crate::arena::model::{Action, Book, Day, Fill, MarketTrade, Name, OpenOrder, Order, Price, Source, Tick};
use crate::support::pyrandom::PyRandom;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TradeMatching {
    All,
    Worse,
    None,
}

/// The price a position is valued at each tick (engine.py's `Mark`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mark {
    Mid,   // the data's mark, else the book's mid
    Touch, // long at the best bid, short at the best ask
    Last,  // the product's last market trade in the data
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum QueueModel {
    Back,
    Prob,
    Front,
}

#[derive(Clone, Copy, Debug)]
pub struct EngineConfig {
    pub trade_matching: TradeMatching,
    pub resting: bool,
    pub queue: QueueModel,
    pub queue_power: f64,
    pub fill_ratio: f64,
    pub seed: i64,
    pub mark: Mark,
    pub limit_penalty: Option<f64>, // None: rule 2's rejection; a rate: charged for each lot beyond a limit, each tick
    pub delay: usize,               // ticks between a bot's decision and its orders reaching the exchange
    pub fee: f64,                   // charged per lot filled
    pub fee_bps: f64,               // charged per fill, in basis points of its value
    pub maker_fee: Option<f64>,     // a passive fill's fee a lot instead of fee (negative: a rebate)
    pub maker_fee_bps: Option<f64>, // a passive fill's basis points instead of fee_bps (negative: a rebate)
}

impl Default for EngineConfig {
    fn default() -> Self {
        EngineConfig {
            trade_matching: TradeMatching::All,
            resting: false,
            queue: QueueModel::Back,
            queue_power: 1.0,
            fill_ratio: 1.0,
            seed: 0,
            mark: Mark::Mid,
            limit_penalty: None,
            delay: 0,
            fee: 0.0,
            fee_bps: 0.0,
            maker_fee: None,
            maker_fee_bps: None,
        }
    }
}

/// What a bot sees of a tick: the book, with the other bots' resting orders in it, and the
/// products that have one in the order the Python bot's dict would list them.
pub struct TickView<'a> {
    pub timestamp: i64,
    pub books: &'a [Option<Book>],
    pub order: &'a [usize],
}

pub trait Bot {
    /// names: the engine's trader names (the day's, then the participants'), which Name indexes.
    fn begin_day(&mut self, _day: &Day, _names: &[String]) {}
    /// Pushes this tick's orders and cancels onto `out` (empty on entry). positions per product;
    /// own_fills since the last call; market_trades the previous tick's, per product; open_orders
    /// this bot's resting orders (always empty in the default mode).
    fn step(&mut self, tick: &TickView, positions: &[i64], own_fills: &[Fill], market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>);
    /// After a step: the exception its Python twin raised there, by type (e.g. "NameError"), if
    /// any. The engine then drops the tick's actions and records the error, as `_call_bot` does.
    fn failed(&mut self) -> Option<String> {
        None
    }
    /// The name of a product index the bot made up for one the day doesn't have (its Python twin
    /// sent an order for that name), for the engine's "order for unknown product" error.
    fn product_name(&self, _product: usize) -> Option<String> {
        None
    }
    /// What an experiment reads from its Python twin's traderData at the end of a day, as JSON
    /// (the template: {product: {"stopped": true}} for each product whose loss stop fired).
    fn memory(&self, _day: &Day) -> Option<String> {
        None
    }
}

#[derive(Default, Debug)]
pub struct DayResult {
    pub timestamps: Vec<i64>,
    // Per product, one value per tick, recorded after that tick's fills.
    pub positions: Vec<Vec<i64>>,
    pub marks: Vec<Vec<f64>>,
    pub pnl: Vec<Vec<f64>>,
    pub best_bids: Vec<Vec<Option<Price>>>,
    pub best_asks: Vec<Vec<Option<Price>>>,
    pub wall_mids: Vec<Vec<Option<f64>>>,
    pub market_trades: Vec<(i64, MarketTrade)>,
    pub orders: Vec<(i64, OpenOrder)>,
    pub cancels: Vec<(i64, u64)>,
    pub fills: Vec<Fill>,
    pub errors: Vec<(i64, String)>,
    pub limit_breaches: Vec<(i64, usize)>,
    pub races: Vec<(i64, usize)>,
}

#[derive(Clone, Debug)]
struct Live {
    id: u64,
    product: usize,
    price: Price,
    quantity: i64,
    timestamp: i64,
    owner: usize,
    ahead: i64,
    seen: i64,
    traded: i64,
}

impl Live {
    fn view(&self) -> OpenOrder {
        OpenOrder { id: self.id, product: self.product, price: self.price, quantity: self.quantity, timestamp: self.timestamp }
    }
}

struct Participant {
    name: Name,
    result: DayResult,
    position: Vec<i64>,
    cash: Vec<f64>,
    unseen_fills: Vec<Fill>,
    market_trades: Vec<Vec<MarketTrade>>, // what it sees next tick
    // This tick's decision: its actions, and the position and open orders it saw.
    actions: Vec<Action>,
    decided_position: Vec<i64>,
    decided_open: Vec<OpenOrder>,
    // With a delay: the decisions on their way to the exchange, oldest first.
    late: VecDeque<Decision>,
}

/// One tick's decision: the actions, and the position and open orders the bot saw.
type Decision = (Vec<Action>, Vec<i64>, Vec<OpenOrder>);

/// One product's book as _liquidity makes it: [price, volume left] levels, reused tick to tick.
#[derive(Default)]
struct Side {
    present: bool,
    bids: Vec<[i64; 2]>,
    asks: Vec<[i64; 2]>,
}

/// A market trade as _liquidity makes it: the trade, its available volume, and what is left of
/// it for our buys (its seller) and for our sells (its buyer).
struct Entry {
    trade: MarketTrade,
    available: i64,
    for_buys: i64,
    for_sells: i64,
}

type Taken = Vec<((usize, bool, Price), i64)>; // (product, buying, price) -> volume, in insertion order

/// Buffers reused from tick to tick, so the loop doesn't allocate (the Python engine builds new
/// lists every tick; the rules don't depend on it).
#[derive(Default)]
struct Scratch {
    fills: Vec<(usize, Fill)>,
    orders: Vec<Order>,
    cancelled: Vec<u64>,
    placed: Vec<Live>,
    queue: Vec<(Price, u8, u64, usize)>,
    buys: Vec<i64>,
    sells: Vec<i64>,
    breached: Vec<usize>,
    raced: Vec<usize>,
    between: Vec<MarketTrade>,
    arrival: Vec<usize>,
    remaining: Vec<Vec<MarketTrade>>,
    taken: Taken,
    priority: Vec<usize>,
    priority_sells: Vec<usize>,
}

pub fn run_day(day: &Day, bot: &mut dyn Bot, config: &EngineConfig) -> DayResult {
    run_market(day, &mut [("you".to_string(), bot)], config).pop().unwrap()
}

pub fn run_market(day: &Day, bots: &mut [(String, &mut dyn Bot)], config: &EngineConfig) -> Vec<DayResult> {
    let n = day.products.len();
    let mut names = day.names.clone();
    let mut intern = |text: &str| -> Name {
        match names.iter().position(|s| s == text) {
            Some(k) => k as Name,
            None => {
                names.push(text.to_string());
                (names.len() - 1) as Name
            }
        }
    };
    let ids: Vec<Name> = bots.iter().map(|(name, _)| intern(name)).collect();
    for (k, id) in ids.iter().enumerate() {
        assert!(!ids[..k].contains(id), "participant names must be unique");
    }
    let mut rng = PyRandom::from_int(config.seed);
    let mut arrival = PyRandom::from_str(&format!("arrival-{}", config.seed));
    let mut players: Vec<Participant> = ids
        .iter()
        .map(|&name| Participant {
            name,
            result: new_result(day),
            position: vec![0; n],
            cash: vec![0.0; n],
            unseen_fills: Vec::new(),
            market_trades: vec![Vec::new(); n],
            actions: Vec::new(),
            decided_position: vec![0; n],
            decided_open: Vec::new(),
            late: (0..config.delay).map(|_| (Vec::new(), vec![0; n], Vec::new())).collect(),
        })
        .collect();
    for (_, bot) in bots.iter_mut() {
        bot.begin_day(day, &names);
    }
    // The fee a lot in engine units: Day.info's unit for decimal prices, else the data's own integer prices.
    let unit: Vec<f64> = (0..n).map(|p| day.info.get(p).copied().flatten().map_or(1.0, |(_, unit)| unit)).collect();
    let lot_fee: Vec<f64> = unit.iter().map(|u| config.fee / u).collect();
    let maker_lot_fee: Option<Vec<f64>> = config.maker_fee.map(|fee| unit.iter().map(|u| fee / u).collect());
    let mut mark = vec![0.0f64; n];
    let mut last: Vec<Option<f64>> = vec![None; n]; // Mark::Last: each product's last market trade
    let mut valued = vec![0.0f64; n];
    let mut resting: Vec<Live> = Vec::new();
    let mut working: Vec<Live> = Vec::new();
    let mut next_id: u64 = 1;
    let mut books: Vec<Side> = (0..n).map(|_| Side::default()).collect();
    let mut trades: Vec<Vec<Entry>> = (0..n).map(|_| Vec::new()).collect();
    let mut s = Scratch { buys: vec![0; n], sells: vec![0; n], remaining: vec![Vec::new(); n], ..Default::default() };

    for tick in &day.ticks {
        let ts = tick.timestamp;
        liquidity(tick, config.fill_ratio, &mut rng, &mut books, &mut trades);
        let mut current: Cow<[Option<Book>]> = Cow::Borrowed(&tick.books);
        if !resting.is_empty() {
            cross(&mut resting, &mut books, ts, &mut s);
            spend_crossed(&mut trades, &s.taken);
            requeue(&mut resting, &tick.books, config.queue, config.queue_power);
            if !s.taken.is_empty() {
                current = Cow::Owned(without(&tick.books, &s.taken));
            }
            resting.retain(|order| order.quantity != 0);
            settle(&mut players, &mut s.fills, config, &lot_fee, maker_lot_fee.as_deref());
        }

        for (i, (player, (_, bot))) in players.iter_mut().zip(bots.iter_mut()).enumerate() {
            player.decided_open.clear();
            player.decided_open.extend(resting.iter().filter(|o| o.owner == i).map(Live::view));
            let (seen, order) = seen_by(&current, &tick.order, &resting, i);
            let view = TickView { timestamp: ts, books: &seen, order: &order };
            player.actions.clear();
            bot.step(&view, &player.position, &player.unseen_fills, &player.market_trades, &player.decided_open, &mut player.actions);
            if let Some(error) = bot.failed() {
                player.actions.clear();
                player.result.errors.push((ts, error));
            }
            player.decided_position.copy_from_slice(&player.position);
            player.unseen_fills.clear();
        }
        if config.delay > 0 {
            // What was decided config.delay ticks ago arrives now; this tick's decision joins the queue.
            for player in players.iter_mut() {
                let mut arrived = player.late.pop_front().expect("one decision per tick of delay");
                std::mem::swap(&mut arrived.0, &mut player.actions);
                std::mem::swap(&mut arrived.1, &mut player.decided_position);
                std::mem::swap(&mut arrived.2, &mut player.decided_open);
                player.late.push_back(arrived);
            }
        }

        // every order on the book this tick, oldest first
        std::mem::swap(&mut working, &mut resting);
        resting.clear();
        s.between.clear();
        s.arrival.clear();
        s.arrival.extend(0..players.len());
        arrival.shuffle(&mut s.arrival);
        for k in 0..s.arrival.len() {
            let i = s.arrival[k];
            let player = &mut players[i];
            cancel(&player.actions, &working, i, &player.decided_open, config.resting, ts, &mut player.result, &mut s.orders, &mut s.cancelled);
            if !s.cancelled.is_empty() {
                working.retain(|o| !s.cancelled.contains(&o.id));
            }
            known(&mut s.orders, n, ts, &mut player.result, &*bots[i].1);
            if config.limit_penalty.is_none() {
                let cancelled = &s.cancelled;
                let seen_left = player.decided_open.iter().filter(|o| !cancelled.contains(&o.id)).map(|o| (o.product, o.quantity));
                breaches(&s.orders, &player.decided_position, seen_left, &day.limits, &mut s.buys, &mut s.sells, &mut s.breached);
                let kept = working.iter().filter(|o| o.owner == i).map(|o| (o.product, o.quantity));
                breaches(&s.orders, &player.position, kept, &day.limits, &mut s.buys, &mut s.sells, &mut s.raced);
                let breached = &s.breached;
                s.raced.retain(|p| !breached.contains(p));
                player.result.limit_breaches.extend(s.breached.iter().map(|&p| (ts, p)));
                player.result.races.extend(s.raced.iter().map(|&p| (ts, p)));
                if !s.breached.is_empty() || !s.raced.is_empty() {
                    let (breached, raced) = (&s.breached, &s.raced);
                    s.orders.retain(|o| !breached.contains(&o.product) && !raced.contains(&o.product));
                }
            }
            s.placed.clear();
            s.placed.extend(s.orders.iter().enumerate().map(|(k, o)| Live {
                id: next_id + k as u64, product: o.product, price: o.price, quantity: o.quantity, timestamp: ts, owner: i, ahead: 0, seen: 0, traded: 0,
            }));
            next_id += s.placed.len() as u64;
            player.result.orders.extend(working.iter().filter(|o| o.owner == i).chain(s.placed.iter()).map(|o| (ts, o.view())));
            for k in 0..s.orders.len() {
                let (ioc, mut live) = (s.orders[k].ioc, s.placed[k].clone());
                take(&mut live, &mut books, &mut working, &ids, ts, &mut s.between, &mut s.queue, &mut s.fills);
                settle(&mut players, &mut s.fills, config, &lot_fee, maker_lot_fee.as_deref());
                if live.quantity != 0 && !(config.resting && ioc) {
                    let volume = volume_at(&live, &current);
                    live.ahead = volume;
                    live.seen = volume;
                    working.push(live); // in the default mode, only until the end of this tick
                }
            }
        }

        if config.resting {
            fill_resting(&mut working, &mut trades, config.trade_matching, ts, &mut s);
            settle(&mut players, &mut s.fills, config, &lot_fee, maker_lot_fee.as_deref());
            working.retain(|o| o.quantity != 0);
            std::mem::swap(&mut working, &mut resting);
        } else if players.len() == 1 {
            // One bot's leftover orders take the trades in the order it sent them: prosperity3bt's rule.
            for order in working.iter_mut() {
                take_trades(order, &mut trades, config.trade_matching, ts, &mut s.fills);
            }
            settle(&mut players, &mut s.fills, config, &lot_fee, maker_lot_fee.as_deref());
        } else {
            match_trades(&mut working, &mut trades, config.trade_matching, ts, &mut s);
            settle(&mut players, &mut s.fills, config, &lot_fee, maker_lot_fee.as_deref());
        }
        working.clear();
        remaining_trades(&trades, &mut s.remaining);
        for player in players.iter_mut() {
            market_view(&s.remaining, &s.between, player.name, &mut player.market_trades);
        }

        for p in 0..n {
            mark[p] = mark_of(tick, &current, p, mark[p]);
            if let Some(trade) = tick.trades[p].last() {
                last[p] = Some(trade.price as f64);
            }
        }
        for player in players.iter_mut() {
            if let Some(rate) = config.limit_penalty {
                charge(player, &day.limits, rate, ts);
            }
            if config.mark == Mark::Mid {
                record(player, tick, &current, &mark);
            } else {
                valued_at(&player.position, &current, &mark, &last, config.mark, &mut valued);
                record(player, tick, &current, &valued);
            }
        }
    }
    players.into_iter().map(|p| p.result).collect()
}

/// EngineConfig.limit_penalty: each lot of a position beyond its limit costs `rate`, this tick.
fn charge(player: &mut Participant, limits: &[i64], rate: f64, ts: i64) {
    for p in 0..limits.len() {
        let over = player.position[p].abs() - limits[p];
        if over > 0 {
            player.cash[p] -= rate * over as f64;
            player.result.limit_breaches.push((ts, p));
        }
    }
}

/// The prices one participant's positions are valued at this tick, by EngineConfig.mark (into `out`).
fn valued_at(position: &[i64], books: &[Option<Book>], mark: &[f64], last: &[Option<f64>], how: Mark, out: &mut [f64]) {
    for p in 0..mark.len() {
        out[p] = match how {
            Mark::Mid => mark[p],
            Mark::Last => last[p].unwrap_or(mark[p]),
            Mark::Touch => {
                let book = books[p].as_ref();
                let best = match position[p] {
                    q if q > 0 => book.and_then(|b| b.bids.first()),
                    q if q < 0 => book.and_then(|b| b.asks.first()),
                    _ => None,
                };
                best.map_or(mark[p], |level| level.0 as f64)
            }
        };
    }
}

fn settle(players: &mut [Participant], fills: &mut Vec<(usize, Fill)>, config: &EngineConfig, lot_fee: &[f64], maker_lot_fee: Option<&[f64]>) {
    for (owner, fill) in fills.drain(..) {
        let player = &mut players[owner];
        player.position[fill.product] += fill.quantity;
        player.cash[fill.product] -= (fill.price * fill.quantity) as f64;
        let passive = fill.source != Source::Book;
        if let (true, Some(maker)) = (passive, maker_lot_fee) {
            player.cash[fill.product] -= maker[fill.product] * fill.quantity.abs() as f64;
        } else if config.fee != 0.0 {
            player.cash[fill.product] -= lot_fee[fill.product] * fill.quantity.abs() as f64;
        }
        if let (true, Some(bps)) = (passive, config.maker_fee_bps) {
            player.cash[fill.product] -= bps * (fill.price * fill.quantity).abs() as f64 / 10_000.0;
        } else if config.fee_bps != 0.0 {
            player.cash[fill.product] -= config.fee_bps * (fill.price * fill.quantity).abs() as f64 / 10_000.0;
        }
        player.result.fills.push(fill);
        player.unseen_fills.push(fill);
    }
}

pub fn new_result(day: &Day) -> DayResult {
    let (n, t) = (day.products.len(), day.ticks.len());
    DayResult {
        timestamps: Vec::with_capacity(t),
        positions: vec![Vec::with_capacity(t); n],
        marks: vec![Vec::with_capacity(t); n],
        pnl: vec![Vec::with_capacity(t); n],
        best_bids: vec![Vec::with_capacity(t); n],
        best_asks: vec![Vec::with_capacity(t); n],
        wall_mids: vec![Vec::with_capacity(t); n],
        ..Default::default()
    }
}

fn record(player: &mut Participant, tick: &Tick, books: &[Option<Book>], mark: &[f64]) {
    let result = &mut player.result;
    result.timestamps.push(tick.timestamp);
    for p in 0..mark.len() {
        result.positions[p].push(player.position[p]);
        result.marks[p].push(mark[p]);
        result.pnl[p].push(player.cash[p] + player.position[p] as f64 * mark[p]);
        let book = books[p].as_ref();
        result.best_bids[p].push(book.and_then(|b| b.bids.first().map(|l| l.0)));
        result.best_asks[p].push(book.and_then(|b| b.asks.first().map(|l| l.0)));
        result.wall_mids[p].push(book.and_then(Book::wall_mid));
    }
    for trades in &tick.trades {
        result.market_trades.extend(trades.iter().map(|&t| (tick.timestamp, t)));
    }
}

/// Applies the cancels: `orders` gets the new orders and `cancelled` the ids cancelled.
#[allow(clippy::too_many_arguments)]
fn cancel(actions: &[Action], working: &[Live], owner: usize, seen: &[OpenOrder], resting_mode: bool, ts: i64, result: &mut DayResult, orders: &mut Vec<Order>, cancelled: &mut Vec<u64>) {
    orders.clear();
    cancelled.clear();
    for action in actions {
        match *action {
            Action::Order(order) => orders.push(order),
            Action::Cancel(id) => {
                let live = working.iter().any(|o| o.owner == owner && o.id == id);
                if live && !cancelled.contains(&id) {
                    cancelled.push(id);
                    result.cancels.push((ts, id));
                } else if !seen.iter().any(|o| o.id == id) {
                    let hint = if resting_mode { "" } else { " (orders only rest in resting mode)" };
                    result.errors.push((ts, format!("cancel for order {id}, which isn't open{hint}")));
                }
            }
        }
    }
}

/// Drops empty orders, and orders for unknown products (an error, naming the product as Python's repr does).
pub fn known(orders: &mut Vec<Order>, products: usize, ts: i64, result: &mut DayResult, bot: &dyn Bot) {
    for order in orders.iter() {
        if order.product >= products {
            let name = bot.product_name(order.product).map_or_else(|| order.product.to_string(), |name| format!("'{name}'"));
            result.errors.push((ts, format!("order for unknown product {name}")));
        }
    }
    orders.retain(|o| o.product < products && o.quantity != 0);
}

/// Products whose new orders could breach the limit (into `out`): all their buys, or all their sells, filling.
pub fn breaches(orders: &[Order], position: &[i64], resting: impl Iterator<Item = (usize, i64)>, limits: &[i64], buys: &mut [i64], sells: &mut [i64], out: &mut Vec<usize>) {
    out.clear();
    if orders.is_empty() {
        return;
    }
    buys.fill(0);
    sells.fill(0);
    for (product, quantity) in orders.iter().map(|o| (o.product, o.quantity)).chain(resting) {
        if quantity > 0 {
            buys[product] += quantity;
        } else {
            sells[product] -= quantity;
        }
    }
    for o in orders {
        let p = o.product;
        if !out.contains(&p) && (position[p] + buys[p] > limits[p] || position[p] - sells[p] < -limits[p]) {
            out.push(p);
        }
    }
    out.sort_unstable();
}

/// Mutable copies of what this tick's orders can trade against, with the fill ratio's draws.
fn liquidity(tick: &Tick, fill_ratio: f64, rng: &mut PyRandom, books: &mut [Side], trades: &mut [Vec<Entry>]) {
    let mut available = |volume: i64| if fill_ratio >= 1.0 { volume } else { rng.binomialvariate(volume, fill_ratio) };
    for (side, book) in books.iter_mut().zip(&tick.books) {
        side.bids.clear();
        side.asks.clear();
        side.present = book.is_some();
        if let Some(b) = book {
            side.bids.extend(b.bids.iter().map(|&(p, v)| [p, available(v)]));
            side.asks.extend(b.asks.iter().map(|&(p, v)| [p, available(v)]));
        }
    }
    for (entries, product_trades) in trades.iter_mut().zip(&tick.trades) {
        entries.clear();
        entries.extend(product_trades.iter().map(|&trade| {
            let volume = available(trade.quantity);
            Entry { trade, available: volume, for_buys: volume, for_sells: volume }
        }));
    }
}

/// Trades a new order against the visible book and other participants' orders, best price first.
#[allow(clippy::too_many_arguments)]
fn take(order: &mut Live, books: &mut [Side], working: &mut [Live], names: &[Name], ts: i64, between: &mut Vec<MarketTrade>, queue: &mut Vec<(Price, u8, u64, usize)>, fills: &mut Vec<(usize, Fill)>) {
    let buying = order.quantity > 0;
    let sign = if buying { 1 } else { -1 };
    let side = &mut books[order.product];
    let levels = if buying { &mut side.asks } else { &mut side.bids }; // empty when there's no book
    // (price key, kind, tie-break, index): the recorded level k, or working[index]
    queue.clear();
    queue.extend(levels.iter().enumerate().map(|(k, l)| (l[0], 0, k as u64, k)));
    for (w, other) in working.iter().enumerate() {
        if other.product == order.product && other.owner != order.owner && (if buying { other.quantity < 0 } else { other.quantity > 0 }) {
            queue.push((other.price, 1, other.id, w));
        }
    }
    if queue.len() > levels.len() {
        queue.sort_by_key(|&(price, kind, tie, _)| (if buying { price } else { -price }, kind, tie));
    } // else the levels alone, already best first

    for &(price, kind, _, index) in queue.iter() {
        if if buying { price > order.price } else { price < order.price } {
            break;
        }
        let take;
        if kind == 0 {
            take = order.quantity.abs().min(levels[index][1]);
            if take == 0 {
                continue;
            }
            levels[index][1] -= take;
            fills.push((order.owner, Fill { timestamp: ts, product: order.product, price, quantity: sign * take, source: Source::Book, counterparty: 0, order_id: order.id }));
        } else {
            let there = &mut working[index];
            take = order.quantity.abs().min(there.quantity.abs());
            if take == 0 {
                continue;
            }
            there.quantity += sign * take;
            let (me, them) = (names[order.owner], names[there.owner]);
            fills.push((order.owner, Fill { timestamp: ts, product: order.product, price, quantity: sign * take, source: Source::Book, counterparty: them, order_id: order.id }));
            fills.push((there.owner, Fill { timestamp: ts, product: order.product, price, quantity: -sign * take, source: Source::Trade, counterparty: me, order_id: there.id }));
            let (buyer, seller) = if buying { (me, them) } else { (them, me) };
            between.push(MarketTrade { product: order.product, price, quantity: take, buyer, seller, timestamp: ts });
        }
        order.quantity -= sign * take;
        if order.quantity == 0 {
            break;
        }
    }
}

/// Fills what's left of the order against market trades at its price or worse, at its own price.
fn take_trades(order: &mut Live, trades: &mut [Vec<Entry>], matching: TradeMatching, ts: i64, fills: &mut Vec<(usize, Fill)>) {
    if matching == TradeMatching::None || order.quantity == 0 {
        return;
    }
    let buying = order.quantity > 0;
    let sign = if buying { 1 } else { -1 };
    for entry in trades[order.product].iter_mut() {
        let trade = entry.trade;
        let better = if buying { trade.price < order.price } else { trade.price > order.price };
        if !(better || (trade.price == order.price && matching == TradeMatching::All)) {
            continue;
        }
        let side = if buying { &mut entry.for_buys } else { &mut entry.for_sells };
        let take = order.quantity.abs().min(*side);
        if take == 0 {
            continue;
        }
        *side -= take;
        order.quantity -= sign * take;
        let counterparty = if buying { trade.seller } else { trade.buyer };
        fills.push((order.owner, Fill { timestamp: ts, product: order.product, price: order.price, quantity: sign * take, source: Source::Trade, counterparty, order_id: order.id }));
        if order.quantity == 0 {
            break;
        }
    }
}

/// Several bots' leftover orders against this tick's market trades, at each order's own price:
/// each trade fills the orders it reaches best price first, then the oldest (`_match_trades`).
fn match_trades(working: &mut [Live], trades: &mut [Vec<Entry>], matching: TradeMatching, ts: i64, s: &mut Scratch) {
    if matching == TradeMatching::None {
        return;
    }
    for (product, entries) in trades.iter_mut().enumerate() {
        if entries.is_empty() {
            continue;
        }
        priority(working, product, true, &mut s.priority);
        priority(working, product, false, &mut s.priority_sells);
        for entry in entries.iter_mut() {
            entry.for_buys = match_queue(working, &s.priority, &entry.trade, entry.for_buys, true, matching, ts, &mut s.fills);
            entry.for_sells = match_queue(working, &s.priority_sells, &entry.trade, entry.for_sells, false, matching, ts, &mut s.fills);
        }
    }
}

/// Fills one side's orders, in priority, from a market trade. Returns the trade volume left over (`_match_queue`).
#[allow(clippy::too_many_arguments)]
fn match_queue(working: &mut [Live], queue: &[usize], trade: &MarketTrade, mut left: i64, buying: bool, matching: TradeMatching, ts: i64, fills: &mut Vec<(usize, Fill)>) -> i64 {
    let sign = if buying { 1 } else { -1 };
    for &k in queue {
        if left == 0 {
            break;
        }
        let order = &mut working[k];
        let size = order.quantity.abs();
        if size == 0 {
            continue;
        }
        let through = if buying { order.price > trade.price } else { order.price < trade.price };
        if !(through || (order.price == trade.price && matching == TradeMatching::All)) {
            break; // the queue is best price first: no later order reaches this trade
        }
        let take = left.min(size);
        order.quantity -= sign * take;
        left -= take;
        let counterparty = if buying { trade.seller } else { trade.buyer };
        fills.push((order.owner, Fill { timestamp: ts, product: trade.product, price: order.price, quantity: sign * take, source: Source::Trade, counterparty, order_id: order.id }));
    }
    left
}

/// Market trades as the bots see them next tick: minus the volume our orders took over.
fn remaining_trades(trades: &[Vec<Entry>], out: &mut [Vec<MarketTrade>]) {
    for (list, entries) in out.iter_mut().zip(trades) {
        list.clear();
        for e in entries {
            let quantity = e.trade.quantity - (e.available - e.for_buys.min(e.for_sells));
            if quantity > 0 {
                list.push(MarketTrade { quantity, ..e.trade });
            }
        }
    }
}

/// The book one participant sees: the tick's plus the other participants' resting orders, and the
/// products with a book in order (one with only others' orders goes last, where Python's dict puts it;
/// Python adds several such in set order, which isn't fixed, and here they go by index).
fn seen_by<'a>(books: &'a [Option<Book>], order: &'a [usize], resting: &[Live], participant: usize) -> (Cow<'a, [Option<Book>]>, Cow<'a, [usize]>) {
    let others: Vec<&Live> = resting.iter().filter(|o| o.owner != participant && o.quantity != 0).collect();
    if others.is_empty() {
        return (Cow::Borrowed(books), Cow::Borrowed(order));
    }
    let mut seen_order = Cow::Borrowed(order);
    let mut out = books.to_vec();
    let mut products: Vec<usize> = others.iter().map(|o| o.product).collect();
    products.sort_unstable();
    products.dedup();
    for p in products {
        let book = books[p].clone().unwrap_or_default();
        let (mut bids, mut asks) = (book.bids, book.asks);
        for order in others.iter().filter(|o| o.product == p) {
            let side = if order.quantity > 0 { &mut bids } else { &mut asks };
            match side.iter_mut().find(|l| l.0 == order.price) {
                Some(level) => level.1 += order.quantity.abs(),
                None => side.push((order.price, order.quantity.abs())),
            }
        }
        bids.sort_by(|a, b| b.0.cmp(&a.0));
        asks.sort_by(|a, b| a.0.cmp(&b.0));
        if out[p].is_none() {
            seen_order.to_mut().push(p);
        }
        out[p] = Some(Book { bids, asks });
    }
    (Cow::Owned(out), seen_order)
}

/// Market trades one participant sees next tick (into `view`): the recorded ones plus other participants' trades.
fn market_view(remaining: &[Vec<MarketTrade>], between: &[MarketTrade], name: Name, view: &mut [Vec<MarketTrade>]) {
    for (list, recorded) in view.iter_mut().zip(remaining) {
        list.clear();
        list.extend_from_slice(recorded);
    }
    for trade in between.iter().filter(|t| t.buyer != name && t.seller != name) {
        view[trade.product].push(*trade);
    }
}

fn mark_of(tick: &Tick, books: &[Option<Book>], product: usize, last: f64) -> f64 {
    if let Some(mark) = tick.marks[product] {
        return mark;
    }
    books[product].as_ref().and_then(Book::mid).unwrap_or(last)
}

// ---------------------------------------------------------------------------- resting mode

/// Price-time priority (into `out`, indices into `live`) among one product's orders on one side:
/// best price first, then the oldest.
fn priority(live: &[Live], product: usize, buying: bool, out: &mut Vec<usize>) {
    out.clear();
    out.extend((0..live.len()).filter(|&k| live[k].product == product && (live[k].quantity > 0) == buying));
    out.sort_by_key(|&k| (if buying { -live[k].price } else { live[k].price }, live[k].id));
}

/// Fills resting orders that the new snapshot's other side reaches, at the resting price (into
/// `s.fills`, and the volume taken per level into `s.taken`).
fn cross(resting: &mut [Live], books: &mut [Side], ts: i64, s: &mut Scratch) {
    s.taken.clear();
    let mut products: Vec<usize> = resting.iter().map(|o| o.product).collect();
    products.sort_unstable();
    products.dedup();
    for product in products {
        for buying in [true, false] {
            let sign = if buying { 1 } else { -1 };
            priority(resting, product, buying, &mut s.priority);
            let side = &mut books[product];
            let levels = if buying { &mut side.asks } else { &mut side.bids };
            for &k in &s.priority {
                let order = &mut resting[k];
                for level in levels.iter_mut() {
                    let (price, volume) = (level[0], level[1]);
                    if if buying { price > order.price } else { price < order.price } {
                        break;
                    }
                    let take = order.quantity.abs().min(volume);
                    if take == 0 {
                        continue;
                    }
                    level[1] -= take;
                    order.quantity -= sign * take;
                    let key = (product, buying, price);
                    match s.taken.iter_mut().find(|(k, _)| *k == key) {
                        Some((_, v)) => *v += take,
                        None => s.taken.push((key, take)),
                    }
                    s.fills.push((order.owner, Fill { timestamp: ts, product, price: order.price, quantity: sign * take, source: Source::Cross, counterparty: 0, order_id: order.id }));
                    if order.quantity == 0 {
                        break;
                    }
                }
            }
        }
    }
}

/// Takes the volume resting orders just crossed off this tick's market trades at the same prices.
fn spend_crossed(trades: &mut [Vec<Entry>], taken: &Taken) {
    for &((product, buying, price), volume) in taken {
        let mut volume = volume;
        for entry in trades[product].iter_mut() {
            if volume == 0 {
                break;
            }
            if entry.trade.price == price {
                let side = if buying { &mut entry.for_buys } else { &mut entry.for_sells };
                let used = volume.min(*side);
                *side -= used;
                volume -= used;
            }
        }
    }
}

/// The books as the bots see them: without the levels resting orders just traded with.
fn without(books: &[Option<Book>], taken: &Taken) -> Vec<Option<Book>> {
    let mut out = books.to_vec();
    let used = |product: usize, buying: bool, price: Price| taken.iter().find(|(k, _)| *k == (product, buying, price)).map_or(0, |(_, v)| *v);
    let minus = |levels: &[(Price, i64)], product: usize, buying: bool| -> Vec<(Price, i64)> {
        levels.iter().filter_map(|&(price, volume)| {
            let u = used(product, buying, price);
            (volume > u).then_some((price, volume - u))
        }).collect()
    };
    let mut products: Vec<usize> = taken.iter().map(|((p, _, _), _)| *p).collect();
    products.sort_unstable();
    products.dedup();
    for p in products {
        let book = books[p].as_ref().expect("a crossed product has a book");
        out[p] = Some(Book { bids: minus(&book.bids, p, false), asks: minus(&book.asks, p, true) });
    }
    out
}

/// Visible volume at the order's price on its own side: what's queued in front of a new order.
fn volume_at(order: &Live, books: &[Option<Book>]) -> i64 {
    let Some(book) = books[order.product].as_ref() else { return 0 };
    let levels = if order.quantity > 0 { &book.bids } else { &book.asks };
    levels.iter().find(|l| l.0 == order.price).map_or(0, |l| l.1)
}

/// Moves resting orders up their queue from the new snapshot (see QueueModel).
fn requeue(resting: &mut [Live], books: &[Option<Book>], model: QueueModel, power: f64) {
    for order in resting.iter_mut() {
        let Some(book) = books[order.product].as_ref() else { continue };
        let buying = order.quantity > 0;
        let levels = if buying { &book.bids } else { &book.asks };
        let better = |a: Price, b: Price| if buying { a > b } else { a < b };
        if levels.is_empty() || better(order.price, levels[0].0) {
            order.ahead = 0; // nothing visible at its price or better: it's at the front
        } else if let Some(&(_, volume)) = levels.iter().find(|l| l.0 == order.price) {
            order.ahead = match model {
                QueueModel::Front => 0,
                QueueModel::Prob => prob_ahead(order, volume, power).min(volume),
                QueueModel::Back => order.ahead.min(volume),
            };
            order.seen = volume;
        } else if better(order.price, levels[levels.len() - 1].0) {
            order.ahead = 0; // its level is inside the visible depth but empty
        }
        order.traded = 0;
    }
}

/// hftbacktest's ProbQueueModel.depth: the volume ahead after the level went from seen to volume.
fn prob_ahead(order: &Live, volume: i64, power: f64) -> i64 {
    let cancelled = order.seen - order.traded - volume;
    if cancelled <= 0 {
        return order.ahead;
    }
    let behind = (order.seen - order.traded - order.ahead).max(0);
    let queue = order.ahead + behind;
    let share = if queue != 0 { (order.ahead as f64 / queue as f64).powf(power) } else { 0.0 };
    let ahead = order.ahead as f64 - share * cancelled as f64 + (behind as f64 - (1.0 - share) * cancelled as f64).min(0.0);
    (ahead.round_ties_even() as i64).max(0)
}

/// Fills resting orders against this tick's market trades, in price-time priority (into `s.fills`).
fn fill_resting(working: &mut [Live], trades: &mut [Vec<Entry>], matching: TradeMatching, ts: i64, s: &mut Scratch) {
    if matching == TradeMatching::None {
        return;
    }
    for (product, entries) in trades.iter_mut().enumerate() {
        if entries.is_empty() {
            continue;
        }
        priority(working, product, true, &mut s.priority);
        priority(working, product, false, &mut s.priority_sells);
        for entry in entries.iter_mut() {
            entry.for_buys = fill_queue(working, &s.priority, &entry.trade, entry.for_buys, true, matching, ts, &mut s.fills);
            entry.for_sells = fill_queue(working, &s.priority_sells, &entry.trade, entry.for_sells, false, matching, ts, &mut s.fills);
        }
    }
}

/// Fills one side's resting orders from a market trade. Returns the trade volume left over.
#[allow(clippy::too_many_arguments)]
fn fill_queue(working: &mut [Live], queue: &[usize], trade: &MarketTrade, mut left: i64, buying: bool, matching: TradeMatching, ts: i64, fills: &mut Vec<(usize, Fill)>) -> i64 {
    let sign = if buying { 1 } else { -1 };
    for &k in queue {
        if left == 0 {
            break;
        }
        let order = &mut working[k];
        let size = order.quantity.abs();
        if size == 0 {
            continue;
        }
        let take;
        if if buying { order.price > trade.price } else { order.price < trade.price } {
            take = left.min(size); // the trade went through its price, so it would have filled first
            order.ahead = 0;
        } else if order.price == trade.price && matching == TradeMatching::All {
            take = 0.max(size.min(left - order.ahead));
            order.traded += left.min(order.ahead);
            order.ahead = 0.max(order.ahead - left);
        } else {
            break;
        }
        if take != 0 {
            order.quantity -= sign * take;
            left -= take;
            let counterparty = if buying { trade.seller } else { trade.buyer };
            fills.push((order.owner, Fill { timestamp: ts, product: trade.product, price: order.price, quantity: sign * take, source: Source::Trade, counterparty, order_id: order.id }));
        }
    }
    left
}
