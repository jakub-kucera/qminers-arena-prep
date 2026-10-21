//! `arena-rs sim`: arena.sim's market on a range of seeds (python/arena/rust.py `run_sim`).

use super::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::{fs, thread};

use arena_rs::arena::engine::{run_market, Bot, DayResult, EngineConfig, TradeMatching};
use arena_rs::arena::model::Day;
use arena_rs::arena::sim;
use arena_rs::support::dayfile;
use arena_rs::support::json::{self};

/// One simulated day for `sim`: the market with the bots, the replays, and the files asked for.
/// Each participant's totals, by name: its PnL (summed over products as Python's `sum` does), each
/// product's in the day's order, its fills, errors (and the first), breaches and races.
pub fn summary(out: &mut String, day: &Day, specs: &[(String, Spec)], results: &[DayResult], bots: &[Box<dyn Bot + Send>]) {
    out.push('{');
    for (j, (((name, _), r), bot)) in specs.iter().zip(results).zip(bots).enumerate() {
        if j > 0 {
            out.push_str(", ");
        }
        json::string(out, name);
        out.push_str(": {\"pnl\": ");
        json::float(out, arena_rs::support::py::sum(day.order.iter().map(|&p| r.pnl[p].last().copied().unwrap_or(0.0))));
        out.push_str(", \"products\": {");
        for (k, &p) in day.order.iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            json::string(out, &day.products[p]);
            out.push_str(": ");
            json::float(out, r.pnl[p].last().copied().unwrap_or(0.0));
        }
        let _ = write!(out, "}}, \"fills\": {}, \"errors\": {}, \"breaches\": {}, \"races\": {}, \"first_error\": ", r.fills.len(), r.errors.len(), r.limit_breaches.len(), r.races.len());
        json::string(out, r.errors.first().map_or("", |(_, e)| e.as_str()));
        out.push_str(", \"memory\": ");
        out.push_str(bot.memory(day).as_deref().unwrap_or("null"));
        out.push('}');
    }
    out.push('}');
}

/// One simulated day for `sim`: the market with the bots, the replays, and the files asked for.
pub fn sim_day(args: &Args, spec: &sim::MarketSpec, specs: &[(String, Spec)], seed: i64, k: usize) -> String {
    let config = args.config();
    let mut built = build_all(specs);
    let inside = sim::run(spec, seed, &mut participants(specs, &mut built), config.resting, None).unwrap_or_else(|e| fail(&e));
    let names = inside.day.names.clone();
    let trades: usize = inside.day.ticks.iter().map(|t| t.trades.iter().map(Vec::len).sum::<usize>()).sum();
    let mut line = format!("{{\"seed\": {seed}, \"day\": {k}, \"trades\": {trades}, \"bots\": ");
    summary(&mut line, &inside.day, specs, &inside.results, &built);
    let out = args.get("--out").map(|dir| format!("{dir}/{}", inside.day.name));
    let write = |path: String, text: String| fs::write(&path, text).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    if let Some(stem) = &out {
        write(format!("{stem}.day"), dayfile::write(&inside.day, &inside.logged, &inside.marks));
        let mut text = String::new();
        for (p, name) in inside.day.products.iter().enumerate() {
            let _ = writeln!(text, "{name} {}", inside.fundamentals[p].iter().map(|v| format!("{v:?}")).collect::<Vec<_>>().join(" "));
        }
        write(format!("{stem}.fundamentals"), text);
        if !specs.is_empty() {
            let mut text = String::new();
            for ((name, _), result) in specs.iter().zip(&inside.results) {
                dump(&mut text, &inside.day, name, result, &names, &Fields::all());
            }
            write(format!("{stem}.dump"), text);
        }
    }
    if args.flags.iter().any(|f| f == "--replay") && !specs.is_empty() {
        let recording = sim::run(spec, seed, &mut [], false, None).unwrap_or_else(|e| fail(&e));
        if let Some(stem) = &out {
            write(format!("{stem}.recording.day"), dayfile::write(&recording.day, &recording.logged, &recording.marks));
        }
        line.push_str(", \"replays\": {");
        for (j, (mode, matching)) in [("all", TradeMatching::All), ("worse", TradeMatching::Worse), ("none", TradeMatching::None)].into_iter().enumerate() {
            let mut built = build_all(specs);
            let results = run_market(&recording.day, &mut participants(specs, &mut built), &EngineConfig { trade_matching: matching, ..config });
            if j > 0 {
                line.push_str(", ");
            }
            let _ = write!(line, "\"{mode}\": ");
            summary(&mut line, &recording.day, specs, &results, &built);
            if let Some(stem) = &out {
                let mut text = String::new();
                for ((name, _), result) in specs.iter().zip(&results) {
                    dump(&mut text, &recording.day, name, result, &bots_names(&recording.day, specs), &Fields::all());
                }
                write(format!("{stem}.replay.{mode}.dump"), text);
            }
        }
        line.push('}');
    }
    line.push('}');
    if let Some(dir) = args.get("--csv") {
        let round: i64 = args.get("--round").unwrap_or("1").parse().unwrap_or_else(|_| fail("--round needs an integer"));
        sim::write_csvs(&inside, std::path::Path::new(dir), round, k as i64).unwrap_or_else(|e| fail(&e));
    }
    line
}

pub fn sim_command(args: &Args) {
    let path = args.days.first().unwrap_or_else(|| fail("sim needs a SPEC.json"));
    let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let spec = json::parse(&text).and_then(|v| sim::MarketSpec::from_json(&v)).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let int = |key: &str, default: &str| -> i64 { args.get(key).unwrap_or(default).parse().unwrap_or_else(|_| fail(&format!("{key} needs an integer"))) };
    let (seed, days, threads) = (int("--market-seed", "0"), int("--days", "1") as usize, int("--threads", "1").max(1) as usize);
    let specs = bot_specs(args);
    for (_, spec) in &specs {
        spec.build().unwrap_or_else(|e| fail(&e)); // refuse settings before running anything
    }
    let next = AtomicUsize::new(0);
    let mut lines = vec![String::new(); days];
    let found: Vec<Vec<(usize, String)>> = thread::scope(|scope| {
        let workers: Vec<_> = (0..threads.min(days.max(1)))
            .map(|_| {
                scope.spawn(|| {
                    let mut mine = Vec::new();
                    loop {
                        let k = next.fetch_add(1, Ordering::Relaxed);
                        if k >= days {
                            break;
                        }
                        mine.push((k, sim_day(args, &spec, &specs, seed + k as i64, k)));
                    }
                    mine
                })
            })
            .collect();
        workers.into_iter().map(|w| w.join().unwrap()).collect()
    });
    for (k, line) in found.into_iter().flatten() {
        lines[k] = line;
    }
    for line in lines {
        println!("{line}");
    }
}
