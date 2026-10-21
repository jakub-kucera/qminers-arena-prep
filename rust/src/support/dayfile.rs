//! Reads a Day exported by experiments/rust_bench.py (`export_day`): the format plug-ins stay in
//! Python, and this is the engine's input, after them. Plain text, whitespace-separated:
//!
//! ```text
//! arena-day 3
//! name <day name>
//! products <n>                       then n lines: <name> <limit>, sorted by name
//! order <product>...                 the Python day's product order
//! limits <product>...                its limits dict's order
//! info <n>                           then n lines: <product> <tick> <unit> (Day.info, for a format with decimal prices)
//! names <n>                          then n lines: one trader name each; the first is the empty name
//! ticks <n>                          then per tick:
//! t <timestamp> <books> <trades> <marks>
//! b <product> <bids> <price> <volume>... <asks> <price> <volume>...   (one line per book)
//! x <product> <price> <quantity> <buyer> <seller> <timestamp>         (one per market trade)
//! m <product> <mark>                                                   (one per mark)
//! ```
//! Products and trader names are indices into those tables. A tick's book lines come in the Python
//! tick's dict order, which a bot sees its products in (order ids depend on it). Version 2 files,
//! without the limits and info lines, still read.

use std::fmt::Write as _;
use std::fs;

use crate::arena::model::{Book, Day, MarketTrade, Tick};
use crate::support::py::Num;

/// A day file, or a day reference (`.json`: a Prosperity day read from its CSVs, src/prosperity.rs).
pub fn load(path: &str) -> Result<Day, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
    if path.ends_with(".json") {
        let reference = crate::support::json::parse(&text).map_err(|e| format!("{path}: {e}"))?;
        return crate::arena::formats::prosperity::load_reference(&reference).map_err(|e| format!("{path}: {e}"));
    }
    parse(&text).map_err(|e| format!("{path}: {e}"))
}

pub fn parse(text: &str) -> Result<Day, String> {
    let mut lines = text.lines();
    let mut next = || lines.next().ok_or_else(|| "unexpected end of file".to_string());
    let version = match next()? {
        "arena-day 2" => 2,
        "arena-day 3" => 3,
        _ => return Err("not an arena-day 3 file (re-export it)".into()),
    };
    let name = next()?.strip_prefix("name ").ok_or("expected name")?.to_string();
    let count = |line: &str, key: &str| -> Result<usize, String> {
        line.strip_prefix(key).and_then(|v| v.trim().parse().ok()).ok_or_else(|| format!("expected {key}<n>, got {line:?}"))
    };
    let n = count(next()?, "products ")?;
    let (mut products, mut limits) = (Vec::new(), Vec::new());
    for _ in 0..n {
        let line = next()?;
        let (product, limit) = line.rsplit_once(' ').ok_or("expected <product> <limit>")?;
        products.push(product.to_string());
        limits.push(limit.parse().map_err(|_| "bad limit")?);
    }
    let line = next()?;
    let order: Vec<usize> = line
        .strip_prefix("order")
        .ok_or_else(|| format!("expected order, got {line:?}"))?
        .split_ascii_whitespace()
        .map(|v| v.parse().map_err(|_| "bad order".to_string()))
        .collect::<Result<_, _>>()?;
    let indices = |line: &str, key: &str| -> Result<Vec<usize>, String> {
        line.strip_prefix(key).ok_or_else(|| format!("expected {key}, got {line:?}"))?.split_ascii_whitespace().map(|v| v.parse().map_err(|_| format!("bad {key}"))).collect()
    };
    let (limits_order, mut info) = (if version >= 3 { indices(next()?, "limits")? } else { order.clone() }, vec![None; n]);
    if version >= 3 {
        for _ in 0..count(next()?, "info ")? {
            let line = next()?;
            let f: Vec<&str> = line.split_ascii_whitespace().collect();
            let [p, tick, unit] = f[..] else { return Err(format!("expected <product> <tick> <unit>, got {line:?}")) };
            let p: usize = p.parse().map_err(|_| "bad info product")?;
            info[p] = Some((tick.parse().map_err(|_| "bad tick")?, unit.parse().map_err(|_| "bad unit")?));
        }
    }
    let names_count = count(next()?, "names ")?;
    let mut names = Vec::new();
    for _ in 0..names_count {
        names.push(next()?.to_string());
    }
    let ticks_count = count(next()?, "ticks ")?;
    let mut ticks = Vec::with_capacity(ticks_count);
    let int = |field: Option<&str>| -> Result<i64, String> { field.and_then(|v| v.parse().ok()).ok_or_else(|| "bad integer".to_string()) };
    for _ in 0..ticks_count {
        let head = next()?;
        let mut f = head.split_ascii_whitespace();
        if f.next() != Some("t") {
            return Err(format!("expected a tick, got {head:?}"));
        }
        let timestamp = int(f.next())?;
        let (nb, nt, nm) = (int(f.next())?, int(f.next())?, int(f.next())?);
        let mut tick = Tick { timestamp, books: vec![None; n], order: Vec::with_capacity(nb as usize), trades: vec![Vec::new(); n], marks: vec![None; n] };
        for _ in 0..nb {
            let line = next()?;
            let mut f = line.split_ascii_whitespace().skip(1);
            let product = int(f.next())? as usize;
            let mut side = || -> Result<Vec<(i64, i64)>, String> {
                let k = int(f.next())?;
                (0..k).map(|_| Ok((int(f.next())?, int(f.next())?))).collect()
            };
            let bids = side()?;
            let asks = side()?;
            tick.books[product] = Some(Book { bids, asks });
            tick.order.push(product);
        }
        for _ in 0..nt {
            let line = next()?;
            let mut f = line.split_ascii_whitespace().skip(1);
            let product = int(f.next())? as usize;
            let (price, quantity, buyer, seller, ts) = (int(f.next())?, int(f.next())?, int(f.next())?, int(f.next())?, int(f.next())?);
            tick.trades[product].push(MarketTrade { product, price, quantity, buyer: buyer as u32, seller: seller as u32, timestamp: ts });
        }
        for _ in 0..nm {
            let line = next()?;
            let mut f = line.split_ascii_whitespace().skip(1);
            let product = int(f.next())? as usize;
            tick.marks[product] = Some(f.next().and_then(|v| v.parse().ok()).ok_or("bad mark")?);
        }
        ticks.push(tick);
    }
    Ok(Day { name, products, limits, order, limits_order, info, ticks, names })
}

/// Writes a day in this format (arena.sim's recordings, for Python to read back): each tick's
/// trades in `trades` order (the order they happened, across products), and its marks as Python
/// holds them (an int for a one-sided book), in the tick's product order.
pub fn write(day: &Day, trades: &[Vec<MarketTrade>], marks: &[Vec<Option<Num>>]) -> String {
    let mut out = String::new();
    let _ = writeln!(out, "arena-day 3\nname {}\nproducts {}", day.name, day.products.len());
    for (name, limit) in day.products.iter().zip(&day.limits) {
        let _ = writeln!(out, "{name} {limit}");
    }
    let _ = writeln!(out, "order{}", day.order.iter().map(|p| format!(" {p}")).collect::<String>());
    let _ = writeln!(out, "limits{}", day.limits_order.iter().map(|p| format!(" {p}")).collect::<String>());
    let info: Vec<(usize, (f64, f64))> = day.info.iter().enumerate().filter_map(|(p, i)| i.map(|i| (p, i))).collect();
    let _ = writeln!(out, "info {}", info.len());
    for (p, (tick, unit)) in info {
        let _ = writeln!(out, "{p} {tick:?} {unit:?}");
    }
    let _ = writeln!(out, "names {}", day.names.len());
    for name in &day.names {
        let _ = writeln!(out, "{name}");
    }
    let _ = writeln!(out, "ticks {}", day.ticks.len());
    let side = |levels: &[(i64, i64)]| format!("{}{}", levels.len(), levels.iter().map(|(p, v)| format!(" {p} {v}")).collect::<String>());
    for (k, tick) in day.ticks.iter().enumerate() {
        let shown: Vec<(usize, Num)> = tick.order.iter().filter_map(|&p| marks[k][p].map(|m| (p, m))).collect();
        let _ = writeln!(out, "t {} {} {} {}", tick.timestamp, tick.order.len(), trades[k].len(), shown.len());
        for &p in &tick.order {
            let book = tick.books[p].as_ref().expect("a product in the order has a book");
            let _ = writeln!(out, "b {p} {} {}", side(&book.bids), side(&book.asks));
        }
        for t in &trades[k] {
            let _ = writeln!(out, "x {} {} {} {} {} {}", t.product, t.price, t.quantity, t.buyer, t.seller, t.timestamp);
        }
        for (p, mark) in shown {
            match mark {
                Num::Int(v) => writeln!(out, "m {p} {v}"),
                Num::Float(v) => writeln!(out, "m {p} {v:?}"),
            }
            .unwrap();
        }
    }
    out
}

/// Writes any day in this format: each tick's trades product by product, its marks as floats.
pub fn write_plain(day: &Day) -> String {
    let trades: Vec<Vec<MarketTrade>> = day.ticks.iter().map(|t| t.trades.iter().flatten().copied().collect()).collect();
    let marks: Vec<Vec<Option<Num>>> = day.ticks.iter().map(|t| t.marks.iter().map(|m| m.map(Num::Float)).collect()).collect();
    write(day, &trades, &marks)
}
