//! What the commands share: the arguments, the bots' specs, the engine's settings, and the JSON
//! dump of a DayResult (python/arena/rust.py reads it).

use std::fmt::Write as _;
use std::{fs, process, thread};

use arena_rs::arena::engine::{Bot, DayResult, EngineConfig, QueueModel, TradeMatching};
use arena_rs::arena::model::Day;
use arena_rs::bots::{self, Requote};
use arena_rs::support::dayfile;
use arena_rs::support::json::{self, Value};

pub struct Args {
    pub days: Vec<String>,
    pub options: Vec<(String, String)>,
    pub flags: Vec<String>,
}

impl Args {
    pub fn parse(raw: &[String]) -> Args {
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

    pub fn get(&self, name: &str) -> Option<&str> {
        self.options.iter().rev().find(|(k, _)| k == name).map(|(_, v)| v.as_str())
    }

    pub fn all(&self, name: &str) -> Vec<&str> {
        self.options.iter().filter(|(k, _)| k == name).map(|(_, v)| v.as_str()).collect()
    }

    pub fn config(&self) -> EngineConfig {
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

pub fn fail(message: &str) -> ! {
    eprintln!("arena-rs: {message}");
    process::exit(2);
}

pub fn queue(text: &str) -> QueueModel {
    match text {
        "back" => QueueModel::Back,
        "prob" => QueueModel::Prob,
        "front" => QueueModel::Front,
        other => fail(&format!("unknown queue model {other}")),
    }
}

pub fn number(text: &str) -> f64 {
    text.parse().unwrap_or_else(|_| fail(&format!("not a number: {text}")))
}

pub fn matching(text: &str) -> TradeMatching {
    match text {
        "all" => TradeMatching::All,
        "worse" => TradeMatching::Worse,
        "none" => TradeMatching::None,
        other => fail(&format!("unknown trade matching {other}")),
    }
}

pub fn load_days(args: &Args) -> Vec<Day> {
    if args.days.is_empty() {
        fail("no day files given");
    }
    load_all(&args.days)
}

/// Day files and references, read on a thread each.
pub fn load_all(paths: &[String]) -> Vec<Day> {
    thread::scope(|scope| {
        let workers: Vec<_> = paths.iter().map(|p| scope.spawn(move || dayfile::load(p))).collect();
        workers.into_iter().map(|w| w.join().unwrap().unwrap_or_else(|e| fail(&e))).collect()
    })
}

/// A bot spec: {"kind": ..., "globals": {...}, "requote": bool}, built fresh for each day.
#[derive(Clone)]
pub struct Spec {
    kind: String,
    globals: Value,
    requote: bool,
}

impl Spec {
    pub fn read(value: &Value) -> Result<Spec, String> {
        let kind = value.get("kind").and_then(Value::as_str).ok_or("a bot spec needs a kind")?.to_string();
        let globals = value.get("globals").cloned().unwrap_or(Value::Object(Vec::new()));
        Ok(Spec { kind, globals, requote: value.get("requote").is_some_and(Value::truthy) })
    }

    pub fn build(&self) -> Result<Box<dyn Bot + Send>, String> {
        let bot = bots::build(&self.kind, &self.globals)?;
        Ok(if self.requote { Box::new(Requote::new(bot)) } else { bot })
    }
}

/// The --bot NAME=SPEC.json options.
pub fn bot_specs(args: &Args) -> Vec<(String, Spec)> {
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
pub fn build_all(specs: &[(String, Spec)]) -> Vec<Box<dyn Bot + Send>> {
    specs.iter().map(|(_, spec)| spec.build().unwrap_or_else(|e| fail(&e))).collect()
}

pub fn participants<'a>(specs: &[(String, Spec)], built: &'a mut [Box<dyn Bot + Send>]) -> Vec<(String, &'a mut dyn Bot)> {
    specs.iter().map(|(n, _)| n.clone()).zip(built.iter_mut().map(|b| b.as_mut() as &mut dyn Bot)).collect()
}

/// The engine's name table: the day's, then each participant not already in it.
pub fn bots_names<T>(day: &Day, specs: &[(String, T)]) -> Vec<String> {
    let mut names = day.names.clone();
    for (name, _) in specs {
        if !names.contains(name) {
            names.push(name.clone());
        }
    }
    names
}

/// The fields `dump` writes: every one, or the --fields list (the rest are written empty).
#[derive(Clone)]
pub struct Fields(Option<Vec<String>>);

impl Fields {
    pub fn of(args: &Args) -> Fields {
        const KNOWN: [&str; 12] = ["fills", "orders", "cancels", "errors", "breaches", "races", "positions", "marks", "pnl", "best_bids", "best_asks", "wall_mids"];
        Fields(args.get("--fields").map(|text| {
            let wanted: Vec<String> = text.split(',').map(str::to_string).collect();
            if let Some(bad) = wanted.iter().find(|f| !KNOWN.contains(&f.as_str())) {
                fail(&format!("unknown field {bad} (fields: {})", KNOWN.join(", ")));
            }
            wanted
        }))
    }

    pub fn all() -> Fields {
        Fields(None)
    }

    pub fn has(&self, field: &str) -> bool {
        self.0.as_ref().is_none_or(|f| f.iter().any(|x| x == field))
    }
}

/// One participant's DayResult as a JSON line (arena/rust.py `read_dump`): every field the parity
/// check compares (those not in `fields` written empty), products and trader names by name, and
/// the day's products in its own order, their limits, and the timestamps.
pub fn dump(out: &mut String, day: &Day, participant: &str, r: &DayResult, names: &[String], fields: &Fields) {
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
    let count = |field: &str, n: usize| if fields.has(field) { n } else { 0 };
    out.push_str("{\"participant\": ");
    json::string(out, participant);
    out.push_str(", \"day\": ");
    json::string(out, &day.name);
    out.push_str(", \"products\": ");
    list(out, day.order.len(), &mut |out, k| json::string(out, product(day.order[k])));
    out.push_str(", \"limits\": ");
    list(out, day.order.len(), &mut |out, k| {
        let _ = write!(out, "{}", day.limits[day.order[k]]);
    });
    out.push_str(", \"timestamps\": ");
    list(out, r.timestamps.len(), &mut |out, k| {
        let _ = write!(out, "{}", r.timestamps[k]);
    });
    out.push_str(", \"fills\": ");
    list(out, count("fills", r.fills.len()), &mut |out, k| {
        let f = &r.fills[k];
        let _ = write!(out, "[{}, ", f.timestamp);
        json::string(out, product(f.product));
        let _ = write!(out, ", {}, {}, \"{}\", {}, ", f.price, f.quantity, f.source.as_str(), f.order_id);
        json::string(out, name(f.counterparty));
        out.push(']');
    });
    out.push_str(", \"orders\": ");
    list(out, count("orders", r.orders.len()), &mut |out, k| {
        let (ts, o) = &r.orders[k];
        let _ = write!(out, "[{ts}, {}, ", o.id);
        json::string(out, product(o.product));
        let _ = write!(out, ", {}, {}, {}]", o.price, o.quantity, o.timestamp);
    });
    out.push_str(", \"cancels\": ");
    list(out, count("cancels", r.cancels.len()), &mut |out, k| {
        let _ = write!(out, "[{}, {}]", r.cancels[k].0, r.cancels[k].1);
    });
    for (label, items) in [("breaches", &r.limit_breaches), ("races", &r.races)] {
        let _ = write!(out, ", \"{label}\": ");
        list(out, count(label, items.len()), &mut |out, k| {
            let _ = write!(out, "[{}, ", items[k].0);
            json::string(out, product(items[k].1));
            out.push(']');
        });
    }
    out.push_str(", \"errors\": ");
    list(out, count("errors", r.errors.len()), &mut |out, k| {
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
        list(out, count("positions", r.positions[p].len()), &mut |out, k| {
            let _ = write!(out, "{}", r.positions[p][k]);
        });
        for (label, values) in [("marks", &r.marks[p]), ("pnl", &r.pnl[p])] {
            let _ = write!(out, ", \"{label}\": ");
            list(out, count(label, values.len()), &mut |out, k| json::float(out, values[k]));
        }
        for (label, values) in [("best_bids", &r.best_bids[p]), ("best_asks", &r.best_asks[p])] {
            let _ = write!(out, ", \"{label}\": ");
            list(out, count(label, values.len()), &mut |out, k| match values[k] {
                Some(v) => {
                    let _ = write!(out, "{v}");
                }
                None => out.push_str("null"),
            });
        }
        out.push_str(", \"wall_mids\": ");
        list(out, count("wall_mids", r.wall_mids[p].len()), &mut |out, k| match r.wall_mids[p][k] {
            Some(v) => json::float(out, v),
            None => out.push_str("null"),
        });
        out.push('}');
    }
    out.push_str("}}\n");
}

pub fn engine_config(value: &Value) -> Result<EngineConfig, String> {
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

pub mod batch;
pub mod day;
pub mod grid;
pub mod run;
pub mod sim;
pub mod stats;

