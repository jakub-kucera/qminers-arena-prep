//! `arena-rs run`: the bots in one market on each day, each made first by --transform if given
//! (arena/stress.rs: a perturbation, or permuted:SEED:BLOCK) (python/arena/rust.py `run_days`, `backtest`).

use super::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::{fs, thread};

use arena_rs::arena::engine::run_market;

pub fn run_command(args: &Args) {
    let config = args.config();
    let specs = bot_specs(args);
    if specs.is_empty() {
        fail("no --bot given");
    }
    for (_, spec) in &specs {
        spec.build().unwrap_or_else(|e| fail(&e)); // refuse settings before running anything
    }
    let threads: usize = args.get("--threads").unwrap_or("1").parse().unwrap_or_else(|_| fail("--threads needs an integer"));
    let fields = Fields::of(args);
    let days = load_days(args);
    let next = AtomicUsize::new(0);
    let found: Vec<Vec<(usize, String, String)>> = thread::scope(|scope| {
        let workers: Vec<_> = (0..threads.clamp(1, days.len()))
            .map(|_| {
                scope.spawn(|| {
                    let mut mine = Vec::new();
                    loop {
                        let k = next.fetch_add(1, Ordering::Relaxed);
                        if k >= days.len() {
                            break;
                        }
                        let day = &days[k];
                        let mut built = build_all(&specs);
                        let results = run_market(day, &mut participants(&specs, &mut built), &config);
                        let names = bots_names(day, &specs);
                        let (mut lines, mut text) = (String::new(), String::new());
                        for ((name, _), result) in specs.iter().zip(&results) {
                            let total: f64 = result.pnl.iter().filter_map(|s| s.last()).sum();
                            let _ = writeln!(lines, "{} {}: pnl {:.1}, {} fills", day.name, name, total, result.fills.len());
                            dump(&mut text, day, name, result, &names, &fields);
                        }
                        mine.push((k, lines, text));
                    }
                    mine
                })
            })
            .collect();
        workers.into_iter().map(|w| w.join().unwrap()).collect()
    });
    let mut ordered: Vec<(usize, String, String)> = found.into_iter().flatten().collect();
    ordered.sort_by_key(|(k, _, _)| *k);
    let mut out = String::new();
    for (_, lines, text) in ordered {
        print!("{lines}");
        out.push_str(&text);
    }
    if let Some(path) = args.get("--dump") {
        fs::write(path, out).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    }
}
