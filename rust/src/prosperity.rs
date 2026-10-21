//! arena/formats/prosperity.py's `load_day`, so a Prosperity day needn't be exported: the prices
//! and trades CSVs read as the Python reads them, to the same Day (books in each timestamp's row
//! order, levels sorted, prices and volumes truncated from floats, a P4 empty book's 0.0 mid no
//! mark, ticks only at timestamps with a price row). The limits come from Python (its LIMITS table
//! and the data's limits.json), in a day reference: {"format": "prosperity", "dir", "round", "day",
//! "limits": {product: limit}, "only": [products] or null} (arena/rust.py `day_file`), `only`
//! keeping those products' books, trades and marks as arena.grid's `only` does.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use crate::json::Value;
use crate::model::{Book, Day, MarketTrade, Tick};

fn read(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Python's `int(float(text))`: the float, truncated toward zero (a whole number read as one).
fn int_of_float(text: &str, path: &Path) -> Result<i64, String> {
    let text = text.trim();
    if let Ok(v) = text.parse::<i64>() {
        return Ok(v);
    }
    text.parse::<f64>().map(|v| v.trunc() as i64).map_err(|_| format!("{}: bad number {text:?}", path.display()))
}

/// A name's index in `names`, added if new.
fn intern(names: &mut Vec<String>, name: &str) -> usize {
    match names.iter().position(|n| n == name) {
        Some(k) => k,
        None => {
            names.push(name.to_string());
            names.len() - 1
        }
    }
}

/// A day reference (see the module's comment), loaded.
pub fn load_reference(reference: &Value) -> Result<Day, String> {
    let dir = reference.get("dir").and_then(Value::as_str).ok_or("a day reference needs a dir")?;
    let round = reference.get("round").and_then(Value::as_i64).ok_or("a day reference needs a round")?;
    let day = reference.get("day").and_then(Value::as_i64).ok_or("a day reference needs a day")?;
    let limits: Vec<(String, i64)> = reference
        .get("limits")
        .and_then(Value::as_object)
        .ok_or("a day reference needs limits")?
        .iter()
        .map(|(p, v)| v.as_i64().map(|v| (p.clone(), v)).ok_or_else(|| format!("the limit of {p} must be an integer")))
        .collect::<Result<_, _>>()?;
    let only: Option<Vec<String>> = match reference.get("only") {
        None | Some(Value::Null) => None,
        Some(v) => Some(v.as_list().ok_or("only must be a list")?.iter().map(|p| p.as_str().map(str::to_string).ok_or("only lists product names")).collect::<Result<_, _>>()?),
    };
    load_day(Path::new(dir), round, day, &limits, only.as_deref())
}

pub fn load_day(data_dir: &Path, round: i64, day: i64, limits: &[(String, i64)], only: Option<&[String]>) -> Result<Day, String> {
    let folder = data_dir.join(format!("round{round}"));
    let prices = folder.join(format!("prices_round_{round}_day_{day}.csv"));
    // per timestamp: (product, book) and (product, mark), in row order; products by first appearance
    let mut seen: Vec<String> = Vec::new();
    let mut books: BTreeMap<i64, Vec<(usize, Book)>> = BTreeMap::new();
    let mut marks: BTreeMap<i64, Vec<(usize, f64)>> = BTreeMap::new();
    for line in read(&prices)?.lines().skip(1) {
        let row: Vec<&str> = line.split(';').collect();
        if row.len() < 16 {
            return Err(format!("{}: a row with {} fields", prices.display(), row.len()));
        }
        let timestamp: i64 = row[1].parse().map_err(|_| format!("{}: bad timestamp {:?}", prices.display(), row[1]))?;
        let product = intern(&mut seen, row[2]);
        let levels = |start: usize| -> Result<Vec<(i64, i64)>, String> {
            let mut out = Vec::new();
            for i in (start..start + 6).step_by(2) {
                if row[i].is_empty() {
                    break;
                }
                out.push((int_of_float(row[i], &prices)?, int_of_float(row[i + 1], &prices)?));
            }
            Ok(out)
        };
        let mut bids = levels(3)?;
        let mut asks = levels(9)?;
        bids.sort_by(|a, b| b.cmp(a));
        asks.sort();
        let book = Book { bids, asks };
        if !row[15].is_empty() {
            let mid: f64 = row[15].trim().parse().map_err(|_| format!("{}: bad mid_price {:?}", prices.display(), row[15]))?;
            if !book.bids.is_empty() || !book.asks.is_empty() || mid != 0.0 {
                set(marks.entry(timestamp).or_default(), product, mid);
            }
        }
        set(books.entry(timestamp).or_default(), product, book);
    }

    let stem = format!("trades_round_{round}_day_{day}");
    let trades_path = [format!("{stem}_wn.csv"), format!("{stem}.csv"), format!("{stem}_nn.csv")].into_iter().map(|n| folder.join(n)).find(|p| p.exists());
    let mut names: Vec<String> = vec![String::new()];
    // per timestamp: (product, trades), products in the order of their first trade
    let mut trades: BTreeMap<i64, Vec<(usize, Vec<(i64, i64, u32, u32)>)>> = BTreeMap::new();
    if let Some(path) = &trades_path {
        for line in read(path)?.lines().skip(1) {
            let row: Vec<&str> = line.split(';').collect();
            if row.len() < 7 {
                return Err(format!("{}: a row with {} fields", path.display(), row.len()));
            }
            let timestamp: i64 = row[0].parse().map_err(|_| format!("{}: bad timestamp {:?}", path.display(), row[0]))?;
            let (buyer, seller) = (intern(&mut names, row[1]) as u32, intern(&mut names, row[2]) as u32);
            let price = int_of_float(row[5], path)?;
            let quantity: i64 = row[6].trim().parse().map_err(|_| format!("{}: bad quantity {:?}", path.display(), row[6]))?;
            let product = intern(&mut seen, row[3]);
            let list = trades.entry(timestamp).or_default();
            match list.iter_mut().find(|(p, _)| *p == product) {
                Some((_, v)) => v.push((price, quantity, buyer, seller)),
                None => list.push((product, vec![(price, quantity, buyer, seller)])),
            }
        }
    }

    // the products with a price row, sorted; seen index -> day index
    let mut priced = vec![false; seen.len()];
    for &(p, _) in books.values().flatten() {
        priced[p] = true;
    }
    let mut products: Vec<String> = seen.iter().zip(&priced).filter(|(_, &on)| on).map(|(p, _)| p.clone()).collect();
    products.sort();
    if let Some(unknown) = products.iter().find(|p| !limits.iter().any(|(q, _)| q == *p)) {
        return Err(format!("no position limit known for {unknown}"));
    }
    if let Some(keep) = only {
        products.retain(|p| keep.contains(p));
    }
    let index: Vec<Option<usize>> = seen.iter().map(|p| products.iter().position(|q| q == p)).collect();
    let index = |p: usize| index[p];
    let n = products.len();
    let mut ticks = Vec::with_capacity(books.len());
    for (&timestamp, rows) in &books {
        let mut tick = Tick { timestamp, books: vec![None; n], order: Vec::new(), trades: vec![Vec::new(); n], marks: vec![None; n] };
        for &(product, ref book) in rows {
            if let Some(k) = index(product) {
                tick.books[k] = Some(book.clone());
                tick.order.push(k);
            }
        }
        for (product, list) in trades.get(&timestamp).into_iter().flatten() {
            if let Some(k) = index(*product) {
                tick.trades[k] = list.iter().map(|&(price, quantity, buyer, seller)| MarketTrade { product: k, price, quantity, buyer, seller, timestamp }).collect();
            }
        }
        for (product, mark) in marks.get(&timestamp).into_iter().flatten() {
            if let Some(k) = index(*product) {
                tick.marks[k] = Some(*mark);
            }
        }
        ticks.push(tick);
    }
    let limits: Vec<i64> = products.iter().map(|p| limits.iter().find(|(q, _)| q == p).unwrap().1).collect();
    Ok(Day {
        name: format!("r{round}d{day}"),
        order: (0..n).collect(),
        limits_order: (0..n).collect(),
        info: vec![None; n],
        products,
        limits,
        ticks,
        names,
    })
}

/// A dict's `d[key] = value`: the key keeps its first place.
fn set<T>(list: &mut Vec<(usize, T)>, key: usize, value: T) {
    match list.iter_mut().find(|(k, _)| *k == key) {
        Some((_, v)) => *v = value,
        None => list.push((key, value)),
    }
}
