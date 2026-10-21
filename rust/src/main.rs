//! arena-rs: the Rust engine and bots on exported days (see README.md).
//!
//!   arena-rs run DAY... [ENGINE] --bot NAME=SPEC.json... [--dump FILE] [--threads N]
//!       the bots in one market on each day, the days on N threads; a SPEC is {"kind", "globals",
//!       "requote"} (arena/rust.py writes them from the Python twin's file); --dump writes each
//!       participant's full DayResult, a JSON line each, day by day (arena/rust.py `run_days`)
//!   arena-rs batch TASKS.json [--threads N]
//!       arena.grid's backtests (arena/rust.py `run_batch`): a JSON line per task on stdout, in order,
//!       with what grid.Piece holds
//!   arena-rs sim SPEC.json [--market-seed S] [--days D] [--threads N] [--bot NAME=SPEC.json]... [--resting] [--queue ...]
//!                [--replay] [--out DIR] [--csv DIR --round R]
//!       arena.sim's market (src/sim.rs; SPEC is `dataclasses.asdict` of a MarketSpec) on seeds S..S+D-1 (--seed is the replays' fill-ratio seed):
//!       --out writes each day's recording (sim<seed>.day, its trades in the order they happened), its
//!       fundamentals and the bots' results (.dump); --replay also runs the bots on the day without them
//!       (.recording.day) under each trade matching (.replay.<mode>.dump); --csv writes the Prosperity layout (arena.sim
//!       generate). A JSON line per day on stdout: each bot's totals in the market and in each replay
//!   arena-rs stats IN.json
//!       arena.grid's statistics (src/stats.rs) on what IN.json holds: {"cscv": {columns, max_splits, seed}},
//!       {"correlation": {scaled}} or {"snooping": {d, q, boot, alpha, seed}}; the answer as JSON on stdout
//!   arena-rs grid DAY... [ENGINE] --make LIST --take LIST [--modes all,worse] [--threads N] [--repeat R]
//!       the market maker (--hold: keeping quotes) on every (day, mode, make_edge, take_edge), one backtest per task on N
//!       threads, R times over for timing: a CSV row per backtest, the timing on stderr
//! ENGINE: --match-trades all|worse|none  --resting  --queue back|prob|front  --queue-power X
//!         --fill-ratio X  --seed N  --product NAME (the product grid varies and trades; default KELP)

use std::fmt::Write as _;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;
use std::{env, fs, process, thread};

use arena_rs::bots::mm::{MarketMaker, Params};
use arena_rs::bots::{self, Requote};
use arena_rs::engine::{run_day, run_market, Bot, DayResult, EngineConfig, QueueModel, TradeMatching};
use arena_rs::json::{self, Value};
use arena_rs::model::Day;
use arena_rs::{dayfile, sim, stats};

struct Args {
    days: Vec<String>,
    options: Vec<(String, String)>,
    flags: Vec<String>,
}

impl Args {
    fn parse(raw: &[String]) -> Args {
        let (mut days, mut options, mut flags) = (Vec::new(), Vec::new(), Vec::new());
        let mut k = 0;
        while k < raw.len() {
            let a = &raw[k];
            if a == "--resting" || a == "--hold" || a == "--replay" {
                flags.push(a.clone());
            } else if a.starts_with("--") {
                let value = raw.get(k + 1).unwrap_or_else(|| fail(&format!("{a} needs a value"))).clone();
                options.push((a.clone(), value));
                k += 1;
            } else {
                days.push(a.clone());
            }
            k += 1;
        }
        Args { days, options, flags }
    }

    fn get(&self, name: &str) -> Option<&str> {
        self.options.iter().rev().find(|(k, _)| k == name).map(|(_, v)| v.as_str())
    }

    fn all(&self, name: &str) -> Vec<&str> {
        self.options.iter().filter(|(k, _)| k == name).map(|(_, v)| v.as_str()).collect()
    }

    fn config(&self) -> EngineConfig {
        EngineConfig {
            trade_matching: self.get("--match-trades").map_or(TradeMatching::All, matching),
            resting: self.flags.iter().any(|f| f == "--resting"),
            queue: queue(self.get("--queue").unwrap_or("back")),
            queue_power: number(self.get("--queue-power").unwrap_or("1")),
            fill_ratio: number(self.get("--fill-ratio").unwrap_or("1")),
            seed: self.get("--seed").unwrap_or("0").parse().unwrap_or_else(|_| fail("--seed needs an integer")),
        }
    }
}

fn fail(message: &str) -> ! {
    eprintln!("arena-rs: {message}");
    process::exit(2);
}

fn queue(text: &str) -> QueueModel {
    match text {
        "back" => QueueModel::Back,
        "prob" => QueueModel::Prob,
        "front" => QueueModel::Front,
        other => fail(&format!("unknown queue model {other}")),
    }
}

fn number(text: &str) -> f64 {
    text.parse().unwrap_or_else(|_| fail(&format!("not a number: {text}")))
}

fn matching(text: &str) -> TradeMatching {
    match text {
        "all" => TradeMatching::All,
        "worse" => TradeMatching::Worse,
        "none" => TradeMatching::None,
        other => fail(&format!("unknown trade matching {other}")),
    }
}

fn load_days(args: &Args) -> Vec<Day> {
    if args.days.is_empty() {
        fail("no day files given");
    }
    args.days.iter().map(|p| dayfile::load(p).unwrap_or_else(|e| fail(&e))).collect()
}

fn main() {
    let raw: Vec<String> = env::args().skip(1).collect();
    let Some(command) = raw.first() else { fail("usage: arena-rs run|grid DAY... (see src/main.rs)") };
    let args = Args::parse(&raw[1..]);
    match command.as_str() {
        "run" => run_command(&args),
        "grid" => grid_command(&args),
        "batch" => batch_command(&args),
        "sim" => sim_command(&args),
        "stats" => stats_command(&args),
        other => fail(&format!("unknown command {other}")),
    }
}

/// A bot spec: {"kind": ..., "globals": {...}, "requote": bool}, built fresh for each day.
#[derive(Clone)]
struct Spec {
    kind: String,
    globals: Value,
    requote: bool,
}

impl Spec {
    fn read(value: &Value) -> Result<Spec, String> {
        let kind = value.get("kind").and_then(Value::as_str).ok_or("a bot spec needs a kind")?.to_string();
        let globals = value.get("globals").cloned().unwrap_or(Value::Object(Vec::new()));
        Ok(Spec { kind, globals, requote: value.get("requote").is_some_and(Value::truthy) })
    }

    fn build(&self) -> Result<Box<dyn Bot + Send>, String> {
        let bot = bots::build(&self.kind, &self.globals)?;
        Ok(if self.requote { Box::new(Requote::new(bot)) } else { bot })
    }
}

/// The --bot NAME=SPEC.json options.
fn bot_specs(args: &Args) -> Vec<(String, Spec)> {
    args.all("--bot")
        .iter()
        .map(|s| {
            let (name, path) = s.split_once('=').unwrap_or_else(|| fail("--bot needs NAME=SPEC.json"));
            let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
            let spec = json::parse(&text).and_then(|v| Spec::read(&v)).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
            (name.to_string(), spec)
        })
        .collect()
}

/// Fresh bots for one market, and the (name, bot) list the engine takes.
fn build_all(specs: &[(String, Spec)]) -> Vec<Box<dyn Bot + Send>> {
    specs.iter().map(|(_, spec)| spec.build().unwrap_or_else(|e| fail(&e))).collect()
}

fn participants<'a>(specs: &[(String, Spec)], built: &'a mut [Box<dyn Bot + Send>]) -> Vec<(String, &'a mut dyn Bot)> {
    specs.iter().map(|(n, _)| n.clone()).zip(built.iter_mut().map(|b| b.as_mut() as &mut dyn Bot)).collect()
}

fn run_command(args: &Args) {
    let config = args.config();
    let specs = bot_specs(args);
    if specs.is_empty() {
        fail("no --bot given");
    }
    for (_, spec) in &specs {
        spec.build().unwrap_or_else(|e| fail(&e)); // refuse settings before running anything
    }
    let threads: usize = args.get("--threads").unwrap_or("1").parse().unwrap_or_else(|_| fail("--threads needs an integer"));
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
                            dump(&mut text, day, name, result, &names);
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

/// The engine's name table: the day's, then each participant not already in it.
fn bots_names<T>(day: &Day, specs: &[(String, T)]) -> Vec<String> {
    let mut names = day.names.clone();
    for (name, _) in specs {
        if !names.contains(name) {
            names.push(name.clone());
        }
    }
    names
}

/// One participant's DayResult as a JSON line (arena/rust.py `read_dump`): every field the parity
/// check compares, products and trader names by name.
fn dump(out: &mut String, day: &Day, participant: &str, r: &DayResult, names: &[String]) {
    let name = |id: u32| names[id as usize].as_str();
    let product = |p: usize| day.products[p].as_str();
    let list = |out: &mut String, n: usize, item: &mut dyn FnMut(&mut String, usize)| {
        out.push('[');
        for k in 0..n {
            if k > 0 {
                out.push_str(", ");
            }
            item(out, k);
        }
        out.push(']');
    };
    out.push_str("{\"participant\": ");
    json::string(out, participant);
    out.push_str(", \"day\": ");
    json::string(out, &day.name);
    out.push_str(", \"fills\": ");
    list(out, r.fills.len(), &mut |out, k| {
        let f = &r.fills[k];
        let _ = write!(out, "[{}, ", f.timestamp);
        json::string(out, product(f.product));
        let _ = write!(out, ", {}, {}, \"{}\", {}, ", f.price, f.quantity, f.source.as_str(), f.order_id);
        json::string(out, name(f.counterparty));
        out.push(']');
    });
    out.push_str(", \"orders\": ");
    list(out, r.orders.len(), &mut |out, k| {
        let (ts, o) = &r.orders[k];
        let _ = write!(out, "[{ts}, {}, ", o.id);
        json::string(out, product(o.product));
        let _ = write!(out, ", {}, {}, {}]", o.price, o.quantity, o.timestamp);
    });
    out.push_str(", \"cancels\": ");
    list(out, r.cancels.len(), &mut |out, k| {
        let _ = write!(out, "[{}, {}]", r.cancels[k].0, r.cancels[k].1);
    });
    for (label, items) in [("breaches", &r.limit_breaches), ("races", &r.races)] {
        let _ = write!(out, ", \"{label}\": ");
        list(out, items.len(), &mut |out, k| {
            let _ = write!(out, "[{}, ", items[k].0);
            json::string(out, product(items[k].1));
            out.push(']');
        });
    }
    out.push_str(", \"errors\": ");
    list(out, r.errors.len(), &mut |out, k| {
        let _ = write!(out, "[{}, ", r.errors[k].0);
        json::string(out, &r.errors[k].1);
        out.push(']');
    });
    let _ = write!(out, ", \"market_trades\": {}, \"series\": {{", r.market_trades.len());
    for (p, product) in day.products.iter().enumerate() {
        if p > 0 {
            out.push_str(", ");
        }
        json::string(out, product);
        out.push_str(": {\"positions\": ");
        list(out, r.positions[p].len(), &mut |out, k| {
            let _ = write!(out, "{}", r.positions[p][k]);
        });
        for (label, values) in [("marks", &r.marks[p]), ("pnl", &r.pnl[p])] {
            let _ = write!(out, ", \"{label}\": ");
            list(out, values.len(), &mut |out, k| json::float(out, values[k]));
        }
        for (label, values) in [("best_bids", &r.best_bids[p]), ("best_asks", &r.best_asks[p])] {
            let _ = write!(out, ", \"{label}\": ");
            list(out, values.len(), &mut |out, k| match values[k] {
                Some(v) => {
                    let _ = write!(out, "{v}");
                }
                None => out.push_str("null"),
            });
        }
        out.push_str(", \"wall_mids\": ");
        list(out, r.wall_mids[p].len(), &mut |out, k| match r.wall_mids[p][k] {
            Some(v) => json::float(out, v),
            None => out.push_str("null"),
        });
        out.push('}');
    }
    out.push_str("}}\n");
}

fn list(text: &str) -> Vec<f64> {
    text.split(',').map(number).collect()
}

fn grid_command(args: &Args) {
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

fn engine_config(value: &Value) -> Result<EngineConfig, String> {
    let text = |key: &str, default: &'static str| value.get(key).map_or(Some(default), Value::as_str).ok_or(format!("config {key} must be a string"));
    let number = |key: &str, default: f64| value.get(key).map_or(Some(default), Value::as_f64).ok_or(format!("config {key} must be a number"));
    Ok(EngineConfig {
        trade_matching: matching(text("trade_matching", "all")?),
        resting: value.get("resting").is_some_and(Value::truthy),
        queue: queue(text("queue", "back")?),
        queue_power: number("queue_power", 1.0)?,
        fill_ratio: number("fill_ratio", 1.0)?,
        seed: value.get("seed").map_or(Some(0), Value::as_i64).ok_or("config seed must be an integer")?,
    })
}

/// grid.block_pnl: a cumulative series cut into `blocks` contiguous blocks, each block's PnL.
fn block_pnl(series: &[f64], blocks: usize) -> Vec<f64> {
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

struct Task {
    day: usize,
    config: EngineConfig,
    bots: Vec<(String, usize)>, // participant name, index into the batch's specs
    blocks: usize,
    fine: usize,
}

/// report.max_drawdown: the largest fall from a running peak.
fn max_drawdown(series: &[f64]) -> f64 {
    let (mut peak, mut drawdown) = (f64::NEG_INFINITY, 0.0);
    for &value in series {
        peak = arena_rs::py::max(peak, value);
        drawdown = arena_rs::py::max(drawdown, peak - value);
    }
    drawdown
}

/// grid._run_piece's Piece for the first participant, as a JSON line, plus each product's max
/// drawdown (arena.stress) and the other participants' totals.
fn piece(day: &Day, results: &[DayResult], blocks: usize, fine: usize) -> String {
    let r = &results[0];
    let ticks = day.ticks.len();
    // report.total_pnl: per tick, Python's sum() over the products in the day's order (compensated, not a plain loop)
    let series: Vec<f64> = if day.order.is_empty() { vec![0.0; ticks] } else { (0..ticks).map(|t| arena_rs::py::sum(day.order.iter().map(|&p| r.pnl[p][t]))).collect() };
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
        json::float(&mut out, arena_rs::py::sum(day.order.iter().map(|&p| other.pnl[p].last().copied().unwrap_or(0.0))));
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

fn batch_command(args: &Args) {
    let path = args.days.first().unwrap_or_else(|| fail("batch needs a TASKS.json"));
    let threads: usize = args.get("--threads").unwrap_or("1").parse().unwrap_or_else(|_| fail("--threads needs an integer"));
    let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let batch = json::parse(&text).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let list = |key: &str| batch.get(key).and_then(Value::as_list).unwrap_or_else(|| fail(&format!("{path}: {key} must be a list")));
    let days: Vec<Day> = list("days").iter().map(|d| dayfile::load(d.as_str().unwrap_or_else(|| fail("days are paths"))).unwrap_or_else(|e| fail(&e))).collect();
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

/// One simulated day for `sim`: the market with the bots, the replays, and the files asked for.
/// Each participant's totals, by name: its PnL (summed over products as Python's `sum` does), each
/// product's in the day's order, its fills, errors (and the first), breaches and races.
fn summary(out: &mut String, day: &Day, specs: &[(String, Spec)], results: &[DayResult]) {
    out.push('{');
    for (j, ((name, _), r)) in specs.iter().zip(results).enumerate() {
        if j > 0 {
            out.push_str(", ");
        }
        json::string(out, name);
        out.push_str(": {\"pnl\": ");
        json::float(out, arena_rs::py::sum(day.order.iter().map(|&p| r.pnl[p].last().copied().unwrap_or(0.0))));
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
        out.push('}');
    }
    out.push('}');
}

/// One simulated day for `sim`: the market with the bots, the replays, and the files asked for.
fn sim_day(args: &Args, spec: &sim::MarketSpec, specs: &[(String, Spec)], seed: i64, k: usize) -> String {
    let config = args.config();
    let mut built = build_all(specs);
    let inside = sim::run(spec, seed, &mut participants(specs, &mut built), config.resting, None).unwrap_or_else(|e| fail(&e));
    let names = inside.day.names.clone();
    let trades: usize = inside.day.ticks.iter().map(|t| t.trades.iter().map(Vec::len).sum::<usize>()).sum();
    let mut line = format!("{{\"seed\": {seed}, \"day\": {k}, \"trades\": {trades}, \"bots\": ");
    summary(&mut line, &inside.day, specs, &inside.results);
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
                dump(&mut text, &inside.day, name, result, &names);
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
            summary(&mut line, &recording.day, specs, &results);
            if let Some(stem) = &out {
                let mut text = String::new();
                for ((name, _), result) in specs.iter().zip(&results) {
                    dump(&mut text, &recording.day, name, result, &bots_names(&recording.day, specs));
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

fn sim_command(args: &Args) {
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

fn matrix(value: Option<&Value>, key: &str) -> Vec<Vec<f64>> {
    let rows = value.and_then(Value::as_list).unwrap_or_else(|| fail(&format!("stats: {key} must be a list of lists")));
    rows.iter()
        .map(|row| row.as_list().unwrap_or_else(|| fail(&format!("stats: {key} must be a list of lists"))).iter().map(|v| v.as_f64().unwrap_or_else(|| fail("stats: numbers only"))).collect())
        .collect()
}

fn stats_command(args: &Args) {
    let path = args.days.first().unwrap_or_else(|| fail("stats needs an IN.json"));
    let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let input = json::parse(&text).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    let int = |v: &Value, key: &str| v.get(key).and_then(Value::as_i64).unwrap_or_else(|| fail(&format!("stats: {key} must be an integer")));
    let float = |v: &Value, key: &str| v.get(key).and_then(Value::as_f64).unwrap_or_else(|| fail(&format!("stats: {key} must be a number")));
    let mut out = String::new();
    if let Some(v) = input.get("cscv") {
        let columns = matrix(v.get("columns"), "columns");
        let r = stats::cscv(&columns, int(v, "max_splits") as usize, int(v, "seed"));
        out.push_str("{\"pbo\": ");
        json::float(&mut out, r.pbo);
        out.push_str(", \"loss\": ");
        json::float(&mut out, r.loss);
        out.push_str(", \"rank\": ");
        json::float(&mut out, r.rank);
        let _ = write!(out, ", \"splits\": {}, \"of\": {}}}", r.splits, r.of);
    } else if let Some(v) = input.get("correlation") {
        match stats::mean_correlation(&matrix(v.get("scaled"), "scaled")) {
            Some(rho) => json::float(&mut out, rho),
            None => out.push_str("null"),
        }
    } else if let Some(v) = input.get("snooping") {
        let d = matrix(v.get("d"), "d");
        let (p, winners) = stats::snooping(&d, float(v, "q"), int(v, "boot") as usize, float(v, "alpha"), int(v, "seed"));
        out.push_str("{\"spa\": {");
        for (k, name) in ["l", "c", "u"].iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            let _ = write!(out, "\"{name}\": ");
            json::float(&mut out, p[k]);
        }
        let _ = write!(out, "}}, \"stepm\": [{}]}}", winners.iter().map(|k| k.to_string()).collect::<Vec<_>>().join(", "));
    } else {
        fail("stats: give cscv, correlation or snooping");
    }
    println!("{out}");
}
