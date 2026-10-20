//! arena-rs: the Rust engine and bots on exported days (see README.md).
//!
//!   arena-rs run DAY... [ENGINE] [--bot NAME=PRODUCT:MAKE:TAKE[:hold][+PRODUCT:...]]... [--dump FILE]
//!       market makers in one market on each day (default: one, `you=KELP:1:1`); --dump writes
//!       each participant's full DayResult for experiments/rust_bench.py's parity check
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
use arena_rs::dayfile;
use arena_rs::engine::{run_day, run_market, Bot, DayResult, EngineConfig, QueueModel, TradeMatching};
use arena_rs::model::Day;

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
            queue: match self.get("--queue").unwrap_or("back") {
                "back" => QueueModel::Back,
                "prob" => QueueModel::Prob,
                "front" => QueueModel::Front,
                other => fail(&format!("unknown queue model {other}")),
            },
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

fn bot_usage() -> ! {
    fail("--bot needs NAME=PRODUCT:MAKE:TAKE[:hold][+PRODUCT:MAKE:TAKE[:hold]...]")
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
        other => fail(&format!("unknown command {other}")),
    }
}

fn run_command(args: &Args) {
    let config = args.config();
    let specs: Vec<(String, Vec<Params>)> = match args.all("--bot") {
        specs if specs.is_empty() => vec![("you".to_string(), vec![Params { product: "KELP".into(), make_edge: 1.0, take_edge: 1.0, hold: false }])],
        specs => specs
            .iter()
            .map(|s| {
                let (name, rest) = s.split_once('=').unwrap_or_else(|| bot_usage());
                let params = rest
                    .split('+')
                    .map(|p| match p.split(':').collect::<Vec<_>>()[..] {
                        [product, make, take] => Params { product: product.to_string(), make_edge: number(make), take_edge: number(take), hold: false },
                        [product, make, take, "hold"] => Params { product: product.to_string(), make_edge: number(make), take_edge: number(take), hold: true },
                        _ => bot_usage(),
                    })
                    .collect();
                (name.to_string(), params)
            })
            .collect(),
    };
    let mut out = String::new();
    for day in load_days(args) {
        let mut makers: Vec<MarketMaker> = specs.iter().map(|(_, params)| MarketMaker::new(params.clone())).collect();
        let mut bots: Vec<(String, &mut dyn Bot)> = specs.iter().map(|(n, _)| n.clone()).zip(makers.iter_mut().map(|m| m as &mut dyn Bot)).collect();
        let results = run_market(&day, &mut bots, &config);
        for ((name, _), result) in specs.iter().zip(&results) {
            let total: f64 = result.pnl.iter().filter_map(|s| s.last()).sum();
            println!("{} {}: pnl {:.1}, {} fills", day.name, name, total, result.fills.len());
            dump(&mut out, &day, name, result, &bots_names(&day, &specs));
        }
    }
    if let Some(path) = args.get("--dump") {
        fs::write(path, out).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    }
}

/// The engine's name table: the day's, then each participant not already in it.
fn bots_names(day: &Day, specs: &[(String, Vec<Params>)]) -> Vec<String> {
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
