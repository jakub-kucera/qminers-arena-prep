//! arena-rs: the Rust engine and bots on exported days (see README.md).
//!
//!   arena-rs run DAY... [ENGINE] --bot NAME=SPEC.json... [--dump FILE]
//!       the bots in one market on each day; a SPEC is {"kind", "globals", "requote"} (arena/rust.py
//!       writes them from the Python twin's file); --dump writes each participant's full DayResult
//!       for the parity check (experiments/rust_bench.py)
//!   arena-rs batch TASKS.json [--threads N]
//!       arena.grid's backtests (arena/rust.py `run_batch`): a JSON line per task on stdout, in order,
//!       with what grid.Piece holds
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
use arena_rs::dayfile;

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
            if a == "--resting" || a == "--hold" {
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

fn run_command(args: &Args) {
    let config = args.config();
    let specs: Vec<(String, Spec)> = args
        .all("--bot")
        .iter()
        .map(|s| {
            let (name, path) = s.split_once('=').unwrap_or_else(|| fail("--bot needs NAME=SPEC.json"));
            let text = fs::read_to_string(path).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
            let spec = json::parse(&text).and_then(|v| Spec::read(&v)).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
            (name.to_string(), spec)
        })
        .collect();
    if specs.is_empty() {
        fail("no --bot given");
    }
    let mut out = String::new();
    for day in load_days(args) {
        let mut built: Vec<Box<dyn Bot + Send>> = specs.iter().map(|(_, spec)| spec.build().unwrap_or_else(|e| fail(&e))).collect();
        let mut bots: Vec<(String, &mut dyn Bot)> = specs.iter().map(|(n, _)| n.clone()).zip(built.iter_mut().map(|b| b.as_mut() as &mut dyn Bot)).collect();
        let results = run_market(&day, &mut bots, &config);
        let names = bots_names(&day, &specs);
        for ((name, _), result) in specs.iter().zip(&results) {
            let total: f64 = result.pnl.iter().filter_map(|s| s.last()).sum();
            println!("{} {}: pnl {:.1}, {} fills", day.name, name, total, result.fills.len());
            dump(&mut out, &day, name, result, &names);
        }
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

fn dump(out: &mut String, day: &Day, participant: &str, r: &DayResult, names: &[String]) {
    let name = |id: u32| names[id as usize].as_str();
    let product = |p: usize| day.products[p].as_str();
    let opt = |v: Option<String>| v.unwrap_or_else(|| "~".to_string());
    let _ = writeln!(out, "participant {} {}", day.name, participant);
    let _ = writeln!(out, "fills {}", r.fills.len());
    for f in &r.fills {
        let _ = writeln!(out, "{} {} {} {} {} {} {}", f.timestamp, product(f.product), f.price, f.quantity, f.source.as_str(), f.order_id, name(f.counterparty));
    }
    let _ = writeln!(out, "orders {}", r.orders.len());
    for (ts, o) in &r.orders {
        let _ = writeln!(out, "{} {} {} {} {} {}", ts, o.id, product(o.product), o.price, o.quantity, o.timestamp);
    }
    let _ = writeln!(out, "cancels {}", r.cancels.len());
    for (ts, id) in &r.cancels {
        let _ = writeln!(out, "{ts} {id}");
    }
    for (label, list) in [("breaches", &r.limit_breaches), ("races", &r.races)] {
        let _ = writeln!(out, "{} {}", label, list.len());
        for (ts, p) in list {
            let _ = writeln!(out, "{} {}", ts, product(*p));
        }
    }
    let _ = writeln!(out, "errors {}", r.errors.len());
    for (ts, e) in &r.errors {
        let _ = writeln!(out, "{ts} {e}");
    }
    let _ = writeln!(out, "market_trades {}", r.market_trades.len());
    for (p, name) in day.products.iter().enumerate() {
        let _ = writeln!(out, "series {name}");
        let join = |v: Vec<String>| v.join(" ");
        let _ = writeln!(out, "{}", join(r.positions[p].iter().map(|x| x.to_string()).collect()));
        let _ = writeln!(out, "{}", join(r.marks[p].iter().map(|x| format!("{x:?}")).collect()));
        let _ = writeln!(out, "{}", join(r.pnl[p].iter().map(|x| format!("{x:?}")).collect()));
        let _ = writeln!(out, "{}", join(r.best_bids[p].iter().map(|x| opt(x.map(|v| v.to_string()))).collect()));
        let _ = writeln!(out, "{}", join(r.best_asks[p].iter().map(|x| opt(x.map(|v| v.to_string()))).collect()));
        let _ = writeln!(out, "{}", join(r.wall_mids[p].iter().map(|x| opt(x.map(|v| format!("{v:?}")))).collect()));
    }
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

/// grid._run_piece's Piece for the first participant, as a JSON line.
fn piece(day: &Day, r: &DayResult, blocks: usize, fine: usize) -> String {
    let ticks = day.ticks.len();
    let series: Vec<f64> = if day.order.is_empty() { vec![0.0; ticks] } else { (0..ticks).map(|t| day.order.iter().fold(0.0, |s, &p| s + r.pnl[p][t])).collect() };
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
    out.push_str(", \"products\": {");
    for (k, &p) in day.order.iter().enumerate() {
        if k > 0 {
            out.push_str(", ");
        }
        json::string(&mut out, &day.products[p]);
        out.push_str(": ");
        json::float(&mut out, r.pnl[p].last().copied().unwrap_or(0.0));
    }
    let _ = write!(out, "}}, \"fills\": {}, \"errors\": {}, \"breaches\": {}, \"first_error\": ", r.fills.len(), r.errors.len(), r.limit_breaches.len());
    json::string(&mut out, r.errors.first().map_or("", |(_, e)| e.as_str()));
    out.push('}');
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
                        mine.push((k, piece(day, &results[0], task.blocks, task.fine)));
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
