//! `arena-rs grid`: bots/mm.rs's make × take grid, for timing (experiments/rust_bench.py).

use super::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;
use std::thread;

use arena_rs::arena::engine::{run_day, EngineConfig, TradeMatching};
use arena_rs::bots::mm::{MarketMaker, Params};

pub fn list(text: &str) -> Vec<f64> {
    text.split(',').map(number).collect()
}

pub fn grid_command(args: &Args) {
    let config = args.config();
    let product = args.get("--product").unwrap_or("KELP").to_string();
    let (make, take) = (list(args.get("--make").unwrap_or("1")), list(args.get("--take").unwrap_or("1")));
    let modes: Vec<(String, TradeMatching)> = args.get("--modes").unwrap_or("all").split(',').map(|m| (m.to_string(), matching(m))).collect();
    let threads: usize = args.get("--threads").unwrap_or("1").parse().unwrap_or_else(|_| fail("--threads needs an integer"));
    let repeat: usize = args.get("--repeat").unwrap_or("1").parse().unwrap_or_else(|_| fail("--repeat needs an integer"));

    let start = Instant::now();
    let days = load_days(args);
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
                            let mut bot = MarketMaker::new(vec![Params { product: product.clone(), make_edge: me, take_edge: te, hold: args.flags.iter().any(|f| f == "--hold") }]);
                            let result = run_day(&days[d], &mut bot, &EngineConfig { trade_matching: modes[m].1, ..config });
                            let total: f64 = result.pnl.iter().filter_map(|s| s.last()).sum();
                            mine.push((k, (total, result.fills.len())));
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
        println!("{},{},{},{},{:?},{}", days[d].name, modes[m].0, me, te, results[k].0, results[k].1);
    }
    let backtests = tasks.len() * repeat;
    eprintln!(
        "{backtests} backtests on {threads} threads in {seconds:.3} s: {:.3} ms of a thread each, {:.0} a second (loading {} days: {load_seconds:.2} s)",
        seconds / backtests as f64 * 1e3 * threads as f64,
        backtests as f64 / seconds,
        days.len()
    );
}
