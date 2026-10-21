//! `arena-rs batch`: arena.grid's, compare's and stress's backtests on N threads (python/arena/rust.py `run_batch`).

use super::*;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::{fs, thread};

use arena_rs::arena::engine::{run_market, Bot, DayResult, EngineConfig};
use arena_rs::arena::model::Day;
use arena_rs::support::json::{self, Value};

/// grid.block_pnl: a cumulative series cut into `blocks` contiguous blocks, each block's PnL.
pub fn block_pnl(series: &[f64], blocks: usize) -> Vec<f64> {
    if series.len() < blocks {
        return Vec::new();
    }
    let mut last = 0.0;
    (0..blocks)
        .map(|k| {
            let end = series[((series.len() * (k + 1)) as f64 / blocks as f64).round_ties_even() as usize - 1];
            let block = end - last;
            last = end;
            block
        })
        .collect()
}

pub struct Task {
    day: usize,
    config: EngineConfig,
    bots: Vec<(String, usize)>, // participant name, index into the batch's specs
    blocks: usize,
    fine: usize,
}

/// report.max_drawdown: the largest fall from a running peak.
pub fn max_drawdown(series: &[f64]) -> f64 {
    let (mut peak, mut drawdown) = (f64::NEG_INFINITY, 0.0);
    for &value in series {
        peak = arena_rs::support::py::max(peak, value);
        drawdown = arena_rs::support::py::max(drawdown, peak - value);
    }
    drawdown
}

/// grid._run_piece's Piece for the first participant, as a JSON line, plus each product's max
/// drawdown (arena.stress) and the other participants' totals.
pub fn piece(day: &Day, results: &[DayResult], blocks: usize, fine: usize) -> String {
    let r = &results[0];
    let ticks = day.ticks.len();
    // report.total_pnl: per tick, Python's sum() over the products in the day's order (compensated, not a plain loop)
    let series: Vec<f64> = if day.order.is_empty() { vec![0.0; ticks] } else { (0..ticks).map(|t| arena_rs::support::py::sum(day.order.iter().map(|&p| r.pnl[p][t]))).collect() };
    let mut out = String::from("{\"pnl\": ");
    json::float(&mut out, series.last().copied().unwrap_or(0.0));
    for (key, list) in [("blocks", block_pnl(&series, blocks)), ("fine", block_pnl(&series, fine))] {
        let _ = write!(out, ", \"{key}\": [");
        for (k, v) in list.iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            json::float(&mut out, *v);
        }
        out.push(']');
    }
    for (key, value) in [("products", &(|p: usize| r.pnl[p].last().copied().unwrap_or(0.0)) as &dyn Fn(usize) -> f64), ("drawdowns", &|p: usize| max_drawdown(&r.pnl[p]))] {
        let _ = write!(out, ", \"{key}\": {{");
        for (k, &p) in day.order.iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            json::string(&mut out, &day.products[p]);
            out.push_str(": ");
            json::float(&mut out, value(p));
        }
        out.push('}');
    }
    let _ = write!(out, ", \"fills\": {}, \"errors\": {}, \"breaches\": {}, \"races\": {}, \"first_error\": ", r.fills.len(), r.errors.len(), r.limit_breaches.len(), r.races.len());
    json::string(&mut out, r.errors.first().map_or("", |(_, e)| e.as_str()));
    out.push_str(", \"others\": [");
    for (k, other) in results[1..].iter().enumerate() {
        if k > 0 {
            out.push_str(", ");
        }
        out.push_str("{\"pnl\": ");
        json::float(&mut out, arena_rs::support::py::sum(day.order.iter().map(|&p| other.pnl[p].last().copied().unwrap_or(0.0))));
        out.push_str(", \"products\": {");
        for (j, &p) in day.order.iter().enumerate() {
            if j > 0 {
                out.push_str(", ");
            }
            json::string(&mut out, &day.products[p]);
            out.push_str(": ");
            json::float(&mut out, other.pnl[p].last().copied().unwrap_or(0.0));
        }
        let _ = write!(out, "}}, \"fills\": {}, \"errors\": {}, \"breaches\": {}, \"races\": {}}}", other.fills.len(), other.errors.len(), other.limit_breaches.len(), other.races.len());
    }
    out.push_str("]}");
    out
}

pub fn batch_command(args: &Args) {
    let path = args.days.first().unwrap_or_else(|| fail("batch needs a TASKS.json"));
    let threads: usize = args.get("--threads").unwrap_or("1").parse().unwrap_or_else(|_| fail("--threads needs an integer"));
    let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let batch = json::parse(&text).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let list = |key: &str| batch.get(key).and_then(Value::as_list).unwrap_or_else(|| fail(&format!("{path}: {key} must be a list")));
    let paths: Vec<String> = list("days").iter().map(|d| d.as_str().unwrap_or_else(|| fail("days are paths")).to_string()).collect();
    let days = load_all(&paths);
    let specs: Vec<Spec> = list("bots").iter().map(|b| Spec::read(b).unwrap_or_else(|e| fail(&e))).collect();
    for spec in &specs {
        spec.build().unwrap_or_else(|e| fail(&e)); // refuse settings before running anything
    }
    let tasks: Vec<Task> = list("tasks")
        .iter()
        .map(|t| {
            let int = |key: &str| t.get(key).and_then(Value::as_i64).unwrap_or_else(|| fail(&format!("a task needs an integer {key}"))) as usize;
            let bots = t
                .get("bots")
                .and_then(Value::as_list)
                .unwrap_or_else(|| fail("a task needs bots"))
                .iter()
                .map(|b| match b.as_list() {
                    Some([Value::Str(name), Value::Int(k)]) => (name.clone(), *k as usize),
                    _ => fail("a task's bots are [name, spec index] pairs"),
                })
                .collect();
            Task { day: int("day"), config: engine_config(t.get("config").unwrap_or(&Value::Null)).unwrap_or_else(|e| fail(&e)), bots, blocks: int("blocks"), fine: int("fine") }
        })
        .collect();

    let next = AtomicUsize::new(0);
    let done = AtomicUsize::new(0);
    let live = std::io::IsTerminal::is_terminal(&std::io::stderr());
    let mut lines = vec![String::new(); tasks.len()];
    let found: Vec<Vec<(usize, String)>> = thread::scope(|scope| {
        let workers: Vec<_> = (0..threads.max(1))
            .map(|_| {
                scope.spawn(|| {
                    let mut mine = Vec::new();
                    loop {
                        let k = next.fetch_add(1, Ordering::Relaxed);
                        if k >= tasks.len() {
                            break;
                        }
                        let task = &tasks[k];
                        let day = &days[task.day];
                        let mut built: Vec<Box<dyn Bot + Send>> = task.bots.iter().map(|(_, s)| specs[*s].build().unwrap()).collect();
                        let mut bots: Vec<(String, &mut dyn Bot)> = task.bots.iter().map(|(n, _)| n.clone()).zip(built.iter_mut().map(|b| b.as_mut() as &mut dyn Bot)).collect();
                        let results = run_market(day, &mut bots, &task.config);
                        mine.push((k, piece(day, &results, task.blocks, task.fine)));
                        let n = done.fetch_add(1, Ordering::Relaxed) + 1;
                        if live && (n % 64 == 0 || n == tasks.len()) {
                            eprint!("\r  {n}/{} backtests", tasks.len());
                        }
                    }
                    mine
                })
            })
            .collect();
        workers.into_iter().map(|w| w.join().unwrap()).collect()
    });
    if live {
        eprint!("\r{}\r", " ".repeat(40));
    }
    for (k, line) in found.into_iter().flatten() {
        lines[k] = line;
    }
    let mut out = String::with_capacity(lines.iter().map(|l| l.len() + 1).sum());
    for line in lines {
        out.push_str(&line);
        out.push('\n');
    }
    print!("{out}");
}
