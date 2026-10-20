//! Reads a Day exported by experiments/rust_bench.py (`export_day`): the format plug-ins stay in
//! Python, and this is the engine's input, after them. Plain text, whitespace-separated:
//!
//! ```text
//! arena-day 2
//! name <day name>
//! products <n>                       then n lines: <name> <limit>, sorted by name
//! order <product>...                 the Python day's product order
//! names <n>                          then n lines: one trader name each; the first is the empty name
//! ticks <n>                          then per tick:
//! t <timestamp> <books> <trades> <marks>
//! b <product> <bids> <price> <volume>... <asks> <price> <volume>...   (one line per book)
//! x <product> <price> <quantity> <buyer> <seller> <timestamp>         (one per market trade)
//! m <product> <mark>                                                   (one per mark)
//! ```
//! Products and trader names are indices into those tables. A tick's book lines come in the Python
//! tick's dict order, which a bot sees its products in (order ids depend on it).

use std::fs;

use crate::model::{Book, Day, MarketTrade, Tick};

pub fn load(path: &str) -> Result<Day, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
    parse(&text).map_err(|e| format!("{path}: {e}"))
}

pub fn parse(text: &str) -> Result<Day, String> {
    let mut lines = text.lines();
    let mut next = || lines.next().ok_or_else(|| "unexpected end of file".to_string());
    if next()? != "arena-day 2" {
        return Err("not an arena-day 2 file (re-export it)".into());
    }
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
    Ok(Day { name, products, limits, order, ticks, names })
}
