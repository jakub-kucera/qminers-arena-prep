//! The Rust half of experiments/rust_bench.py: mm.py's market maker and the engine's default mode
//! (arena/engine.py: orders live one tick; the limit check cancels a product's orders; each order
//! takes the book at the book's prices, then what is left meets the tick's market trades at its
//! own price under `all` or `worse`). One participant, fill ratio 1: the rest of the engine isn't
//! ported.
//!
//! usage: rust_mm DAY_FILE... --make 0,1,... --take 0,1,... --modes all,worse --threads N --repeat R
//! Each day file is one tick per line, as experiments/rust_bench.py exports it:
//! `mark nbids (price volume)... nasks (price volume)... ntrades (price quantity)...`.
//! Prints one CSV row per (day, mode, make_edge, take_edge): the final PnL and the fill count,
//! then the time per backtest on stderr.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;
use std::{env, fs, thread};

const LIMIT: i64 = 50;

struct Tick {
    mark: f64,
    bids: Vec<(i64, i64)>, // best first, as Book holds them
    asks: Vec<(i64, i64)>,
    trades: Vec<(i64, i64)>,
}

#[derive(Clone, Copy)]
enum Mode {
    All,
    Worse,
}

struct Order {
    price: i64,
    quantity: i64,
}

fn wall(levels: &[(i64, i64)]) -> i64 {
    let mut best = levels[0];
    for &level in &levels[1..] {
        if level.1 > best.1 {
            best = level;
        }
    }
    best.0
}

/// mm.py's Trader.run.
fn strategy(tick: &Tick, position: i64, make_edge: f64, take_edge: f64, orders: &mut Vec<Order>) {
    orders.clear();
    if tick.bids.is_empty() || tick.asks.is_empty() {
        return;
    }
    let fair = (wall(&tick.bids) + wall(&tick.asks)) as f64 / 2.0;
    let (mut buy_room, mut sell_room) = (LIMIT - position, LIMIT + position);
    for &(price, volume) in &tick.asks {
        if price as f64 > fair - take_edge || buy_room == 0 {
            break;
        }
        let quantity = volume.min(buy_room);
        orders.push(Order { price, quantity });
        buy_room -= quantity;
    }
    for &(price, volume) in &tick.bids {
        if (price as f64) < fair + take_edge || sell_room == 0 {
            break;
        }
        let quantity = volume.min(sell_room);
        orders.push(Order { price, quantity: -quantity });
        sell_room -= quantity;
    }
    let bid = (tick.bids[0].0 + 1).min((fair - make_edge).floor() as i64);
    let ask = (tick.asks[0].0 - 1).max((fair + make_edge).ceil() as i64);
    if buy_room > 0 {
        orders.push(Order { price: bid, quantity: buy_room });
    }
    if sell_room > 0 {
        orders.push(Order { price: ask, quantity: -sell_room });
    }
}

/// One backtest: the final PnL (cash plus position at the mark) and the number of fills.
fn run_day(day: &[Tick], make_edge: f64, take_edge: f64, mode: Mode) -> (f64, usize) {
    let (mut position, mut cash, mut fills, mut pnl) = (0i64, 0.0f64, 0usize, 0.0f64);
    let mut orders = Vec::new();
    let mut working: Vec<(i64, i64)> = Vec::new();
    let (mut bids_left, mut asks_left): (Vec<i64>, Vec<i64>) = (Vec::new(), Vec::new());
    let (mut for_buys, mut for_sells): (Vec<i64>, Vec<i64>) = (Vec::new(), Vec::new());
    for tick in day {
        strategy(tick, position, make_edge, take_edge, &mut orders);
        let buys: i64 = orders.iter().filter(|o| o.quantity > 0).map(|o| o.quantity).sum();
        let sells: i64 = orders.iter().filter(|o| o.quantity < 0).map(|o| -o.quantity).sum();
        if position + buys > LIMIT || position - sells < -LIMIT {
            orders.clear(); // engine._breaches: every order for the product is rejected
        }
        bids_left.clear();
        bids_left.extend(tick.bids.iter().map(|l| l.1));
        asks_left.clear();
        asks_left.extend(tick.asks.iter().map(|l| l.1));
        for_buys.clear();
        for_buys.extend(tick.trades.iter().map(|t| t.1));
        for_sells.clear();
        for_sells.extend(tick.trades.iter().map(|t| t.1));
        working.clear();
        for order in &orders {
            let buying = order.quantity > 0;
            let sign = if buying { 1 } else { -1 };
            let (levels, left) = if buying { (&tick.asks, &mut asks_left) } else { (&tick.bids, &mut bids_left) };
            let mut rest = order.quantity.abs();
            for (k, &(price, _)) in levels.iter().enumerate() {
                if (buying && price > order.price) || (!buying && price < order.price) {
                    break;
                }
                let take = rest.min(left[k]);
                if take == 0 {
                    continue;
                }
                left[k] -= take;
                position += sign * take;
                cash -= (price * sign * take) as f64;
                fills += 1;
                rest -= take;
                if rest == 0 {
                    break;
                }
            }
            if rest > 0 {
                working.push((order.price, sign * rest));
            }
        }
        for &(price, quantity) in &working {
            let buying = quantity > 0;
            let sign = if buying { 1 } else { -1 };
            let side = if buying { &mut for_buys } else { &mut for_sells };
            let mut rest = quantity.abs();
            for (k, &(trade_price, _)) in tick.trades.iter().enumerate() {
                let better = if buying { trade_price < price } else { trade_price > price };
                if !(better || (trade_price == price && matches!(mode, Mode::All))) {
                    continue;
                }
                let take = rest.min(side[k]);
                if take == 0 {
                    continue;
                }
                side[k] -= take;
                position += sign * take;
                cash -= (price * sign * take) as f64;
                fills += 1;
                rest -= take;
                if rest == 0 {
                    break;
                }
            }
        }
        pnl = cash + position as f64 * tick.mark;
    }
    (pnl, fills)
}

fn load(path: &str) -> Vec<Tick> {
    let text = fs::read_to_string(path).expect("day file");
    text.lines()
        .map(|line| {
            let mut fields = line.split_ascii_whitespace();
            let mark: f64 = fields.next().unwrap().parse().unwrap();
            let mut pairs = || {
                let n: usize = fields.next().unwrap().parse().unwrap();
                (0..n)
                    .map(|_| (fields.next().unwrap().parse().unwrap(), fields.next().unwrap().parse().unwrap()))
                    .collect::<Vec<(i64, i64)>>()
            };
            let (bids, asks, trades) = (pairs(), pairs(), pairs());
            Tick { mark, bids, asks, trades }
        })
        .collect()
}

fn floats(text: &str) -> Vec<f64> {
    text.split(',').map(|v| v.parse().unwrap()).collect()
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let option = |name: &str, default: &str| -> String {
        args.iter().position(|a| a == name).map(|k| args[k + 1].clone()).unwrap_or(default.to_string())
    };
    let paths: Vec<&String> = args.iter().take_while(|a| !a.starts_with("--")).collect();
    let (make, take) = (floats(&option("--make", "1")), floats(&option("--take", "1")));
    let modes: Vec<(String, Mode)> = option("--modes", "all")
        .split(',')
        .map(|m| (m.to_string(), if m == "worse" { Mode::Worse } else { Mode::All }))
        .collect();
    let threads: usize = option("--threads", "1").parse().unwrap();
    let repeat: usize = option("--repeat", "1").parse().unwrap();

    let start = Instant::now();
    let days: Vec<Vec<Tick>> = paths.iter().map(|p| load(p)).collect();
    let load_seconds = start.elapsed().as_secs_f64();

    let mut tasks = Vec::new();
    for d in 0..days.len() {
        for m in 0..modes.len() {
            for &me in &make {
                for &te in &take {
                    tasks.push((d, m, me, te));
                }
            }
        }
    }
    let mut results = vec![(0.0, 0usize); tasks.len()];
    let start = Instant::now();
    for _ in 0..repeat {
        let next = AtomicUsize::new(0);
        let found: Vec<Vec<(usize, (f64, usize))>> = thread::scope(|scope| {
            let workers: Vec<_> = (0..threads)
                .map(|_| {
                    scope.spawn(|| {
                        let mut mine = Vec::new();
                        loop {
                            let k = next.fetch_add(1, Ordering::Relaxed);
                            if k >= tasks.len() {
                                break;
                            }
                            let (d, m, me, te) = tasks[k];
                            mine.push((k, run_day(&days[d], me, te, modes[m].1)));
                        }
                        mine
                    })
                })
                .collect();
            workers.into_iter().map(|w| w.join().unwrap()).collect()
        });
        for (k, result) in found.into_iter().flatten() {
            results[k] = result;
        }
    }
    let seconds = start.elapsed().as_secs_f64();

    println!("day,mode,make_edge,take_edge,pnl,fills");
    for (k, &(d, m, me, te)) in tasks.iter().enumerate() {
        println!("{},{},{},{},{:.6},{}", d, modes[m].0, me, te, results[k].0, results[k].1);
    }
    let backtests = tasks.len() * repeat;
    eprintln!(
        "{} backtests on {} threads in {:.4} s: {:.1} us each, {:.0} a second (loading {} days: {:.3} s)",
        backtests,
        threads,
        seconds,
        seconds / backtests as f64 * 1e6 * threads as f64,
        backtests as f64 / seconds,
        days.len(),
        load_seconds
    );
}
