//! `arena-rs batch`: arena.grid's, compare's and stress's backtests on N threads (python/arena/rust.py
//! `run_batch`). A task's "transform" (arena/stress.rs) makes its day a perturbed or permuted copy,
//! each distinct one made once. A task's "set" ([[path, value], ...], arena.grid's combination), or its
//! "cell" (an index into the batch's "cells", a list of sets), is applied to its first bot's globals
//! here, as `--set` is to a Python bot, so a grid sends one spec for all its cells. A task's "config"
//! is an engine config or an index into the batch's "configs". With `--binary PATH` each result goes to
//! that file as soon as it is made, in `piece_binary`'s layout after its task's index, which
//! python/arena/rust.py reads without JSON.

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
    transform: Option<String>, // arena/stress.rs `transform` of the day, made once per batch
    config: usize,             // index into the batch's configs
    bots: Vec<(String, usize)>, // participant name, index into the batch's specs
    blocks: usize,
    fine: usize,
    cell: Option<usize>, // index into the batch's cells: overrides of the first bot's globals (botfile._apply_override's rules)
}

/// A set: [[path, value], ...].
fn read_set(value: &Value) -> Vec<(String, Value)> {
    value
        .as_list()
        .unwrap_or_else(|| fail("a set is a list of [path, value] pairs"))
        .iter()
        .map(|pair| match pair.as_list() {
            Some([Value::Str(path), value]) => (path.clone(), value.clone()),
            _ => fail("a set is a list of [path, value] pairs"),
        })
        .collect()
}

/// The first participant's Piece in the binary layout python/arena/rust.py `read_pieces` reads, little-endian:
/// pnl f64; the blocks (u32 count, f64s); the fine blocks (u32, f64s); each product's PnL in the day's
/// order (u32, f64s); fills, errors, breaches and races (u32 each); the first error (u32 length, UTF-8).
pub fn piece_binary(day: &Day, results: &[DayResult], blocks: usize, fine: usize, out: &mut Vec<u8>) {
    let r = &results[0];
    let ticks = day.ticks.len();
    let series: Vec<f64> = if day.order.is_empty() { vec![0.0; ticks] } else { (0..ticks).map(|t| arena_rs::support::py::sum(day.order.iter().map(|&p| r.pnl[p][t]))).collect() };
    let floats = |out: &mut Vec<u8>, values: &[f64]| {
        out.extend_from_slice(&(values.len() as u32).to_le_bytes());
        for v in values {
            out.extend_from_slice(&v.to_le_bytes());
        }
    };
    out.extend_from_slice(&series.last().copied().unwrap_or(0.0).to_le_bytes());
    floats(out, &block_pnl(&series, blocks));
    floats(out, &block_pnl(&series, fine));
    floats(out, &day.order.iter().map(|&p| r.pnl[p].last().copied().unwrap_or(0.0)).collect::<Vec<f64>>());
    for n in [r.fills.len(), r.errors.len(), r.limit_breaches.len(), r.races.len()] {
        out.extend_from_slice(&(n as u32).to_le_bytes());
    }
    let error = r.errors.first().map_or("", |(_, e)| e.as_str()).as_bytes();
    out.extend_from_slice(&(error.len() as u32).to_le_bytes());
    out.extend_from_slice(error);
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
    // the file and its JSON tree are let go once read: a large grid's tasks would hold them through the run
    let (paths, specs, configs, cells, mut tasks) = {
        let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
        let batch = json::parse(&text).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
        let list = |key: &str| batch.get(key).and_then(Value::as_list).unwrap_or_else(|| fail(&format!("{path}: {key} must be a list")));
        let paths: Vec<String> = list("days").iter().map(|d| d.as_str().unwrap_or_else(|| fail("days are paths")).to_string()).collect();
        let specs: Vec<Spec> = list("bots").iter().map(|b| Spec::read(b).unwrap_or_else(|e| fail(&e))).collect();
        let mut configs: Vec<EngineConfig> =
            batch.get("configs").and_then(Value::as_list).map_or_else(Vec::new, |l| l.iter().map(|c| engine_config(c).unwrap_or_else(|e| fail(&e))).collect());
        let mut cells: Vec<Vec<(String, Value)>> = batch.get("cells").and_then(Value::as_list).map_or_else(Vec::new, |l| l.iter().map(read_set).collect());
        let mut tasks = Vec::new();
        for t in list("tasks") {
            let int = |key: &str| t.get(key).and_then(Value::as_i64).unwrap_or_else(|| fail(&format!("a task needs an integer {key}"))) as usize;
            let index = |k: i64, n: usize, what: &str| if (0..n as i64).contains(&k) { k as usize } else { fail(&format!("a task's {what} {k} is out of range")) };
            let bots = t
                .get("bots")
                .and_then(Value::as_list)
                .unwrap_or_else(|| fail("a task needs bots"))
                .iter()
                .map(|b| match b.as_list() {
                    Some([Value::Str(name), Value::Int(k)]) => (name.clone(), index(*k, specs.len(), "bot")),
                    _ => fail("a task's bots are [name, spec index] pairs"),
                })
                .collect();
            let transform = t.get("transform").and_then(Value::as_str).map(str::to_string);
            let config = match t.get("config") {
                Some(Value::Int(k)) => index(*k, configs.len(), "config"),
                other => {
                    configs.push(engine_config(other.unwrap_or(&Value::Null)).unwrap_or_else(|e| fail(&e)));
                    configs.len() - 1
                }
            };
            let cell = match (t.get("cell"), t.get("set")) {
                (Some(Value::Int(k)), _) => Some(index(*k, cells.len(), "cell")),
                (_, Some(set)) => {
                    cells.push(read_set(set));
                    Some(cells.len() - 1)
                }
                _ => None,
            };
            tasks.push(Task { day: int("day"), transform, config, bots, blocks: int("blocks"), fine: int("fine"), cell });
        }
        (paths, specs, configs, cells, tasks)
    };
    let mut days = load_all(&paths);
    for spec in &specs {
        spec.build().unwrap_or_else(|e| fail(&e)); // refuse settings before running anything
    }

    // each distinct (day, transform) made once, on a thread each, and the tasks pointed at it
    let mut made: Vec<(usize, String)> = Vec::new();
    for task in tasks.iter_mut() {
        if let Some(spec) = task.transform.take() {
            let key = (task.day, spec);
            let k = made.iter().position(|m| *m == key).unwrap_or_else(|| {
                made.push(key);
                made.len() - 1
            });
            task.day = days.len() + k;
        }
    }
    let transformed: Vec<Day> = thread::scope(|scope| {
        let days = &days;
        let workers: Vec<_> = made.iter().map(|(d, spec)| scope.spawn(move || arena_rs::arena::stress::transform(&days[*d], spec))).collect();
        workers.into_iter().map(|w| w.join().unwrap().unwrap_or_else(|e| fail(&e))).collect()
    });
    days.extend(transformed);
    // refuse a bad path or value before running anything: each distinct override on its own (arena.grid's
    // smoke test has run the first combination in Python)
    let mut checked: Vec<((usize, &String), Vec<&Value>)> = Vec::new(); // (spec, path) -> the values checked
    let mut pairs: std::collections::HashSet<(usize, usize)> = std::collections::HashSet::new();
    for task in &tasks {
        let Some(cell) = task.cell else { continue };
        if !pairs.insert((task.bots[0].1, cell)) {
            continue;
        }
        for (k, (path, value)) in cells[cell].iter().enumerate() {
            let key = (task.bots[0].1, path);
            let at = match checked.get(k) {
                Some((seen, _)) if *seen == key => k, // the axes come in the same order in every task
                _ => checked.iter().position(|(seen, _)| *seen == key).unwrap_or_else(|| {
                    checked.push((key, Vec::new()));
                    checked.len() - 1
                }),
            };
            if !checked[at].1.contains(&value) {
                checked[at].1.push(value);
                specs[key.0].with_set(&[(path.clone(), value.clone())]).and_then(|s| s.build()).unwrap_or_else(|e| fail(&e));
            }
        }
    }
    let binary = args.get("--binary");
    // binary results are written as they come, each after its task's index, so none is held
    let file = binary.map(|path| std::sync::Mutex::new(std::io::BufWriter::new(fs::File::create(path).unwrap_or_else(|e| fail(&format!("{path}: {e}"))))));
    let next = AtomicUsize::new(0);
    let done = AtomicUsize::new(0);
    let live = std::io::IsTerminal::is_terminal(&std::io::stderr());
    let mut lines = vec![Vec::new(); if binary.is_some() { 0 } else { tasks.len() }];
    let found: Vec<Vec<(usize, Vec<u8>)>> = thread::scope(|scope| {
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
                        let mut built: Vec<Box<dyn Bot + Send>> = task
                            .bots
                            .iter()
                            .enumerate()
                            .map(|(j, (_, s))| {
                                let made = match task.cell {
                                    Some(cell) if j == 0 => specs[*s].with_set(&cells[cell]).and_then(|spec| spec.build()),
                                    _ => specs[*s].build(),
                                };
                                made.unwrap_or_else(|e| fail(&e))
                            })
                            .collect();
                        let mut bots: Vec<(String, &mut dyn Bot)> = task.bots.iter().map(|(n, _)| n.clone()).zip(built.iter_mut().map(|b| b.as_mut() as &mut dyn Bot)).collect();
                        let results = run_market(day, &mut bots, &configs[task.config]);
                        if let Some(file) = &file {
                            let mut bytes = (k as u32).to_le_bytes().to_vec();
                            piece_binary(day, &results, task.blocks, task.fine, &mut bytes);
                            use std::io::Write as _;
                            file.lock().unwrap().write_all(&bytes).unwrap_or_else(|e| fail(&e.to_string()));
                        } else {
                            let mut bytes = piece(day, &results, task.blocks, task.fine).into_bytes();
                            bytes.push(b'\n');
                            mine.push((k, bytes));
                        }
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
    use std::io::Write as _;
    if let Some(file) = file {
        file.into_inner().unwrap().flush().unwrap_or_else(|e| fail(&e.to_string()));
        return;
    }
    for (k, line) in found.into_iter().flatten() {
        lines[k] = line;
    }
    let mut out = std::io::BufWriter::new(std::io::stdout().lock());
    for line in lines {
        out.write_all(&line).unwrap_or_else(|e| fail(&e.to_string()));
    }
    out.flush().unwrap_or_else(|e| fail(&e.to_string()));
}
