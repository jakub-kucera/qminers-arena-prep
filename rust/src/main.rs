//! arena-rs: the Rust engine and bots on exported days (see README.md).
//!
//!   arena-rs run DAY... [ENGINE] --bot NAME=SPEC.json... [--dump FILE] [--fields LIST] [--threads N]
//!       the bots in one market on each day, the days on N threads; a SPEC is {"kind", "globals",
//!       "requote"} (python/arena/rust.py writes them from the Python twin's file); --dump writes each
//!       participant's DayResult, a JSON line each, day by day (python/arena/rust.py `run_days`), with only
//!       the --fields listed (e.g. pnl,errors,breaches) if given
//!   arena-rs batch TASKS.json [--threads N]
//!       arena.grid's backtests (python/arena/rust.py `run_batch`): a JSON line per task on stdout, in order,
//!       with what grid.Piece holds
//!   arena-rs sim SPEC.json [--market-seed S] [--days D] [--threads N] [--bot NAME=SPEC.json]... [--resting] [--queue ...]
//!                [--replay] [--out DIR] [--csv DIR --round R]
//!       arena.sim's market (src/arena/sim.rs; SPEC is `dataclasses.asdict` of a MarketSpec) on seeds S..S+D-1 (--seed is the replays' fill-ratio seed):
//!       --out writes each day's recording (sim<seed>.day, its trades in the order they happened), its
//!       fundamentals and the bots' results (.dump); --replay also runs the bots on the day without them
//!       (.recording.day) under each trade matching (.replay.<mode>.dump); --csv writes the Prosperity layout (arena.sim
//!       generate). A JSON line per day on stdout: each bot's totals in the market and in each replay
//!   arena-rs day DAY... --out DIR
//!       each day (a day file, or a day reference read from its CSVs) written back as a day file, DIR/<name>.day
//!   arena-rs stats IN.json
//!       arena.grid's statistics (src/arena/stats.rs) on what IN.json holds: {"cscv": {columns, max_splits, seed}},
//!       {"correlation": {scaled}} or {"snooping": {d, q, boot, alpha, seed}}; the answer as JSON on stdout
//!   arena-rs grid DAY... [ENGINE] --make LIST --take LIST [--modes all,worse] [--threads N] [--repeat R]
//!       the market maker (--hold: keeping quotes) on every (day, mode, make_edge, take_edge), one backtest per task on N
//!       threads, R times over for timing: a CSV row per backtest, the timing on stderr
//! ENGINE: --match-trades all|worse|none  --resting  --queue back|prob|front  --queue-power X
//!         --fill-ratio X  --seed N  --mark mid|touch|last  --limit-penalty RATE  --delay TICKS
//!         --fee PER_LOT  --fee-bps BPS  --maker-fee PER_LOT  --maker-fee-bps BPS (a passive fill's, negative a rebate)
//!         --deplete (volume taken from the recorded book stays gone while its level shows more)
//!         --product NAME (grid only: the product it varies and trades; default KELP)

mod commands;

use std::env;

use commands::*;

fn main() {
    let raw: Vec<String> = env::args().skip(1).collect();
    let Some(command) = raw.first() else { fail("usage: arena-rs run|batch|sim|stats|day|grid ... (see src/main.rs)") };
    let args = Args::parse(&raw[1..]);
    match command.as_str() {
        "run" => run::run_command(&args),
        "grid" => grid::grid_command(&args),
        "batch" => batch::batch_command(&args),
        "sim" => sim::sim_command(&args),
        "stats" => stats::stats_command(&args),
        "day" => day::day_command(&args),
        other => fail(&format!("unknown command {other}")),
    }
}
