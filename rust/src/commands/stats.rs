//! `arena-rs stats`: the grid's statistics (python/arena/rust.py `cscv`, `mean_correlation`, `snooping`, and
//! `spa`, `stepm`, `scales` on their own, as experiments/snooping_tests.py calls them).

use super::*;
use std::fs;

use arena_rs::arena::stats;
use arena_rs::support::json::{self, Value};

pub fn matrix(value: Option<&Value>, key: &str) -> Vec<Vec<f64>> {
    let rows = value.and_then(Value::as_list).unwrap_or_else(|| fail(&format!("stats: {key} must be a list of lists")));
    rows.iter()
        .map(|row| row.as_list().unwrap_or_else(|| fail(&format!("stats: {key} must be a list of lists"))).iter().map(|v| v.as_f64().unwrap_or_else(|| fail("stats: numbers only"))).collect())
        .collect()
}

pub fn stats_command(args: &Args) {
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
    } else if let Some(v) = input.get("spa") {
        // spa(d, q, boot, seed): its own studentization and resamples
        let d = matrix(v.get("d"), "d");
        let q = float(v, "q");
        let p = stats::spa(&d, &stats::scales(&d, q), &stats::bootstrap_means(&d, q, int(v, "boot") as usize, int(v, "seed")));
        out.push('{');
        for (k, name) in ["l", "c", "u"].iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            let _ = write!(out, "\"{name}\": ");
            json::float(&mut out, p[k]);
        }
        out.push('}');
    } else if let Some(v) = input.get("stepm") {
        // stepm(d, q, boot, alpha, seed): its own studentization and resamples
        let d = matrix(v.get("d"), "d");
        let q = float(v, "q");
        let winners = stats::stepm(&d, &stats::scales(&d, q), &stats::bootstrap_means(&d, q, int(v, "boot") as usize, int(v, "seed")), float(v, "alpha"));
        let _ = write!(out, "[{}]", winners.iter().map(|k| k.to_string()).collect::<Vec<_>>().join(", "));
    } else if let Some(v) = input.get("scales") {
        let scales = stats::scales(&matrix(v.get("d"), "d"), float(v, "q"));
        out.push('[');
        for (k, w) in scales.iter().enumerate() {
            if k > 0 {
                out.push_str(", ");
            }
            json::float(&mut out, *w);
        }
        out.push(']');
    } else {
        fail("stats: give cscv, correlation, snooping, spa, stepm or scales");
    }
    println!("{out}");
}
