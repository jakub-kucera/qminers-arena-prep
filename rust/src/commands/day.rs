//! `arena-rs day`: days and references written back as day files (python/arena/rust.py `prosperity_day`).

use super::*;
use std::fs;

use arena_rs::support::dayfile;

pub fn day_command(args: &Args) {
    let dir = args.get("--out").unwrap_or_else(|| fail("day needs --out DIR"));
    for day in load_days(args) {
        let path = format!("{dir}/{}.day", day.name);
        fs::write(&path, dayfile::write_plain(&day)).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    }
}
