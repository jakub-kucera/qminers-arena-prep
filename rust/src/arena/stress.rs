//! python/arena/stress.py's perturbations and `permute`, function for function: the same days to
//! the bit (offsets on each product's tick grid, Python's `round` and `statistics.median`, the
//! permutation's shuffle from `random.Random(seed)`), so arena.stress, arena.grid's permutation
//! test and the experiments can make their days in Rust. The command line and the running stay in
//! Python.

use crate::arena::model::{wall, Book, Day, Tick};
use crate::support::pyrandom::PyRandom;

pub const PERTURBATIONS: [&str; 8] = ["vol2", "trend_up", "trend_down", "shift_up", "shift_down", "spike_up", "spike_down", "no_wall"];
const SPIKE_TICKS: usize = 100;

/// Python's `round(x)`: an int, ties to even.
fn round(x: f64) -> i64 {
    x.round_ties_even() as i64
}

/// `perturb`: a copy of the day with one perturbation applied to every product.
pub fn perturb(day: &Day, name: &str, size: f64) -> Result<Day, String> {
    if !PERTURBATIONS.contains(&name) {
        return Err(format!("unknown perturbation {name:?}: choose from {}", PERTURBATIONS.join(", ")));
    }
    let n = day.ticks.len();
    let mut out = copy(day, format!("{}/{name}", day.name));
    if name == "no_wall" {
        let (start, end) = ((0.4 * n as f64) as usize, (0.6 * n as f64) as usize);
        for (k, tick) in out.ticks.iter_mut().enumerate() {
            if start <= k && k < end {
                for book in tick.books.iter_mut().flatten() {
                    *book = without_walls(book);
                }
            }
        }
        return Ok(out);
    }
    let offsets: Vec<Vec<i64>> = (0..day.products.len()).map(|p| offsets(day, p, name, size)).collect();
    for (k, tick) in out.ticks.iter_mut().enumerate() {
        shift(tick, |p| offsets[p][k]);
    }
    Ok(out)
}

/// `permute`: the day's own ticks in a shuffled order, in runs of `block` ticks, each shifted so
/// that its wall bid continues from the previous copied tick's by the move it had in the real day.
pub fn permute(day: &Day, seed: i64, block: usize) -> Day {
    let n = day.ticks.len();
    let mut runs: Vec<Vec<usize>> = (0..n).step_by(block.max(1)).map(|k| (k..(k + block).min(n)).collect()).collect();
    PyRandom::from_int(seed).shuffle(&mut runs);
    let order: Vec<usize> = runs.into_iter().flatten().collect();
    let offsets: Vec<Vec<i64>> = (0..day.products.len())
        .map(|p| {
            let walls = forward_fill(day.ticks.iter().map(|t| t.books[p].as_ref().filter(|b| !b.bids.is_empty()).map(|b| wall(&b.bids))));
            let Some(first) = walls.iter().flatten().next().copied() else { return vec![0; n] };
            let walls: Vec<i64> = walls.iter().map(|w| w.unwrap_or(first)).collect();
            let moves: Vec<i64> = (0..n).map(|k| if k == 0 { 0 } else { walls[k] - walls[k - 1] }).collect();
            let mut level = walls[0]; // the level before the first tick (whose own move is 0)
            order.iter().map(|&k| {
                level += moves[k];
                level - walls[k]
            }).collect()
        })
        .collect();
    let mut out = copy(day, format!("{}/permuted{seed}", day.name));
    out.ticks = order
        .iter()
        .enumerate()
        .map(|(j, &k)| {
            let mut tick = clone_tick(&day.ticks[k]);
            shift(&mut tick, |p| offsets[p][j]);
            let stamp = day.ticks[j].timestamp;
            tick.timestamp = stamp;
            for trade in tick.trades.iter_mut().flatten() {
                trade.timestamp = stamp;
            }
            tick
        })
        .collect();
    out
}

/// `_offsets`: a product's offset at each tick, in its ticks.
fn offsets(day: &Day, p: usize, name: &str, size: f64) -> Vec<i64> {
    let n = day.ticks.len();
    let walls = forward_fill(day.ticks.iter().map(|t| t.books[p].as_ref().and_then(Book::wall_mid)));
    let mut spreads: Vec<i64> = day.ticks.iter().filter_map(|t| t.books[p].as_ref().filter(|b| !b.bids.is_empty() && !b.asks.is_empty()).map(|b| b.asks[0].0 - b.bids[0].0)).collect();
    // max(statistics.median(spreads), 1), else 1
    let s = if spreads.is_empty() {
        1.0
    } else {
        spreads.sort_unstable();
        let m = spreads.len();
        let median = if m % 2 == 1 { spreads[m / 2] as f64 } else { (spreads[m / 2 - 1] + spreads[m / 2]) as f64 / 2.0 };
        if 1.0 > median { 1.0 } else { median }
    };
    let tick = tick_of(day, p);
    let sign = if name.ends_with("_down") { -1.0 } else { 1.0 };
    let half = n / 2;
    let on_grid = |x: f64| round(x / tick as f64) * tick; // offsets move prices by whole ticks, so the book stays on its grid
    if name == "vol2" {
        let first = walls.iter().flatten().next().copied();
        return walls.iter().map(|w| match (w, first) {
            (Some(w), Some(first)) => on_grid(size * (w - first)),
            _ => 0,
        }).collect();
    }
    if name.starts_with("trend") {
        return (0..n).map(|k| on_grid(sign * 10.0 * s * size * k as f64 / (n.saturating_sub(1).max(1)) as f64)).collect();
    }
    if name.starts_with("shift") {
        return (0..n).map(|k| if k >= half { on_grid(sign * 5.0 * s * size) } else { 0 }).collect();
    }
    (0..n).map(|k| if half <= k && k < half + SPIKE_TICKS { on_grid(sign * 5.0 * s * size) } else { 0 }).collect() // spike
}

/// `_tick`: the product's price increment, the gcd of the gaps between its prices (1 if none).
fn tick_of(day: &Day, p: usize) -> i64 {
    let mut prices: Vec<i64> = day.ticks.iter().filter_map(|t| t.books[p].as_ref()).flat_map(|b| b.bids.iter().chain(&b.asks).map(|l| l.0)).collect();
    prices.sort_unstable();
    prices.dedup();
    let gcd = prices.windows(2).map(|w| w[1] - w[0]).fold(0, |a, b| {
        let (mut a, mut b) = (a, b);
        while b != 0 {
            (a, b) = (b, a % b);
        }
        a
    });
    if gcd == 0 { 1 } else { gcd }
}

fn forward_fill<T: Copy>(values: impl Iterator<Item = Option<T>>) -> Vec<Option<T>> {
    let mut last = None;
    values.map(|v| {
        if v.is_some() {
            last = v;
        }
        last
    }).collect()
}

/// `_shifted`: every product's book, trades and mark moved by its offset.
fn shift(tick: &mut Tick, offset: impl Fn(usize) -> i64) {
    for (p, book) in tick.books.iter_mut().enumerate() {
        let d = offset(p);
        if let (Some(book), true) = (book, d != 0) {
            for level in book.bids.iter_mut().chain(book.asks.iter_mut()) {
                level.0 += d;
            }
        }
    }
    for (p, trades) in tick.trades.iter_mut().enumerate() {
        let d = offset(p);
        for trade in trades.iter_mut() {
            trade.price += d;
        }
    }
    for (p, mark) in tick.marks.iter_mut().enumerate() {
        if let Some(m) = mark {
            *m += offset(p) as f64;
        }
    }
}

/// `_without_walls`: each side without its largest level (the first of equals), if it has two or more.
fn without_walls(book: &Book) -> Book {
    let drop_largest = |levels: &[(i64, i64)]| -> Vec<(i64, i64)> {
        if levels.len() < 2 {
            return levels.to_vec();
        }
        let mut largest = 0;
        for k in 1..levels.len() {
            if levels[k].1 > levels[largest].1 {
                largest = k;
            }
        }
        levels.iter().enumerate().filter(|&(k, _)| k != largest).map(|(_, &l)| l).collect()
    };
    Book { bids: drop_largest(&book.bids), asks: drop_largest(&book.asks) }
}

fn clone_tick(tick: &Tick) -> Tick {
    Tick { timestamp: tick.timestamp, books: tick.books.clone(), order: tick.order.clone(), trades: tick.trades.clone(), marks: tick.marks.clone() }
}

fn copy(day: &Day, name: String) -> Day {
    Day {
        name,
        products: day.products.clone(),
        limits: day.limits.clone(),
        order: day.order.clone(),
        limits_order: day.limits_order.clone(),
        info: day.info.clone(),
        ticks: day.ticks.iter().map(clone_tick).collect(),
        names: day.names.clone(),
    }
}

/// A day transformed as a task asks: "perturbation[:size]" (perturb) or "permuted:seed:block" (permute).
pub fn transform(day: &Day, spec: &str) -> Result<Day, String> {
    let parts: Vec<&str> = spec.split(':').collect();
    let number = |text: &str| text.parse::<f64>().map_err(|_| format!("bad number in transform {spec:?}"));
    match parts.as_slice() {
        ["permuted", seed, block] => Ok(permute(day, seed.parse().map_err(|_| format!("bad seed in {spec:?}"))?, block.parse().map_err(|_| format!("bad block in {spec:?}"))?)),
        [name] => perturb(day, name, 1.0),
        [name, size] => perturb(day, name, number(size)?),
        _ => Err(format!("a transform is NAME[:SIZE] or permuted:SEED:BLOCK, not {spec:?}")),
    }
}
