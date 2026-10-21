//! `arena-rs day DAY... --out DIR [--transform SPEC]`: days and references written back as day files,
//! DIR/<name>.day with any / in the name as _ (python/arena/rust.py `prosperity_day`; the loader's and
//! the stress transforms' parity checks).

use super::*;
use std::fs;

use arena_rs::support::dayfile;

pub fn day_command(args: &Args) {
    let dir = args.get("--out").unwrap_or_else(|| fail("day needs --out DIR"));
    for day in load_days(args) {
        let path = format!("{dir}/{}.day", day.name.replace('/', "_")); // a perturbed day is named r1d0/trend_up
        fs::write(&path, dayfile::write_plain(&day)).unwrap_or_else(|e| fail(&format!("{path}: {e}")));
    }
}
