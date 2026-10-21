//! python/bots/zoo/ in Rust: one twin per LLM-written bot, translated line by line (the Python files are
//! never edited, so each twin is a translation the parity check holds to its original). They
//! don't read settings from the Python file (rust/twins.json marks them "settings": false, and
//! python/arena/rust.py refuses `--set` on them): a zoo bot is run as written.
//!
//! What the Prosperity format hands a bot, as these twins read it: `state.order_depths` in the
//! tick's order (`TickView::order`), each with `buy_orders` (the book's bids, best first) and
//! `sell_orders` (its asks, best first, volumes negative); `state.position` (0 if absent).
//! Python's own arithmetic, where it isn't IEEE's, is in `py`.

pub use crate::support::py;

#[path = "chatgpt/gpt-5-6-luna_baseline.rs"]
mod gpt_5_6_luna_baseline;
#[path = "chatgpt/gpt-5-6-luna_market_maker.rs"]
mod gpt_5_6_luna_market_maker;
#[path = "claude/haiku-5.5_baseline.rs"]
mod haiku_5_5_baseline;
#[path = "claude/opus-5.5_baseline.rs"]
mod opus_5_5_baseline;
#[path = "claude/opus-5.5_market_maker.rs"]
mod opus_5_5_market_maker;
#[path = "claude/opus-5.5_mean_reversion.rs"]
mod opus_5_5_mean_reversion;
#[path = "claude/opus-5.5_momentum.rs"]
mod opus_5_5_momentum;
#[path = "claude/sonnet-5.5_baseline.rs"]
mod sonnet_5_5_baseline;
#[path = "gemini/gemini-3-8-flash-high_baseline.rs"]
mod gemini_3_8_flash_high_baseline;
#[path = "gemini/gemini-3-8-flash-high_market_maker.rs"]
mod gemini_3_8_flash_high_market_maker;
#[path = "other/deepseek-r1-14b_baseline.rs"]
mod deepseek_r1_14b_baseline;
#[path = "other/deepseek-r1-14b_baseline_2.rs"]
mod deepseek_r1_14b_baseline_2;
#[path = "other/deepseek-r1-14b_market_maker.rs"]
mod deepseek_r1_14b_market_maker;
#[path = "other/deepseek-r1-14b_market_maker_2.rs"]
mod deepseek_r1_14b_market_maker_2;
#[path = "other/gemma4-26b_baseline.rs"]
mod gemma4_26b_baseline;
#[path = "other/gemma4-26b_baseline_2.rs"]
mod gemma4_26b_baseline_2;
#[path = "other/gemma4-26b_market_maker.rs"]
mod gemma4_26b_market_maker;
#[path = "other/gemma4-26b_market_maker_2.rs"]
mod gemma4_26b_market_maker_2;
#[path = "other/gpt-oss-120B_baseline.rs"]
mod gpt_oss_120b_baseline;
#[path = "other/gpt-oss-120B_market_maker.rs"]
mod gpt_oss_120b_market_maker;
#[path = "other/gpt-oss-20b_baseline.rs"]
mod gpt_oss_20b_baseline;
#[path = "other/gpt-oss-20b_baseline_2.rs"]
mod gpt_oss_20b_baseline_2;
#[path = "other/gpt-oss-20b_market_maker.rs"]
mod gpt_oss_20b_market_maker;
#[path = "other/gpt-oss-20b_market_maker_2.rs"]
mod gpt_oss_20b_market_maker_2;
#[path = "other/phi4-14b_baseline.rs"]
mod phi4_14b_baseline;
#[path = "other/phi4-14b_baseline_2.rs"]
mod phi4_14b_baseline_2;
#[path = "other/phi4-14b_market_maker.rs"]
mod phi4_14b_market_maker;
#[path = "other/phi4-14b_market_maker_2.rs"]
mod phi4_14b_market_maker_2;
#[path = "other/qwen3.8-27b-medium_baseline.rs"]
mod qwen3_8_27b_medium_baseline;
#[path = "other/qwen3.8-27b-medium_baseline_2.rs"]
mod qwen3_8_27b_medium_baseline_2;
#[path = "other/qwen3.8-27b-medium_market_maker.rs"]
mod qwen3_8_27b_medium_market_maker;
#[path = "other/qwen3.8-27b-medium_market_maker_2.rs"]
mod qwen3_8_27b_medium_market_maker_2;

use crate::arena::engine::Bot;
use crate::arena::model::{Action, Book, Day, Order, Price};

/// A zoo bot by its kind, `zoo/<folder>/<file stem>` (rust/twins.json).
pub fn build(kind: &str) -> Option<Box<dyn Bot + Send>> {
    Some(match kind {
        "zoo/claude/haiku-5.5_baseline" => Box::new(haiku_5_5_baseline::Bot::default()),
        "zoo/claude/opus-5.5_baseline" => Box::new(opus_5_5_baseline::Bot::default()),
        "zoo/claude/opus-5.5_market_maker" => Box::new(opus_5_5_market_maker::Bot::default()),
        "zoo/claude/opus-5.5_mean_reversion" => Box::new(opus_5_5_mean_reversion::Bot::default()),
        "zoo/claude/opus-5.5_momentum" => Box::new(opus_5_5_momentum::Bot::default()),
        "zoo/claude/sonnet-5.5_baseline" => Box::new(sonnet_5_5_baseline::Bot::default()),
        "zoo/chatgpt/gpt-5-6-luna_baseline" => Box::new(gpt_5_6_luna_baseline::Bot::default()),
        "zoo/chatgpt/gpt-5-6-luna_market_maker" => Box::new(gpt_5_6_luna_market_maker::Bot::default()),
        "zoo/gemini/gemini-3-8-flash-high_baseline" => Box::new(gemini_3_8_flash_high_baseline::Bot::default()),
        "zoo/gemini/gemini-3-8-flash-high_market_maker" => Box::new(gemini_3_8_flash_high_market_maker::Bot::default()),
        "zoo/other/deepseek-r1-14b_baseline" => Box::new(deepseek_r1_14b_baseline::Bot::default()),
        "zoo/other/deepseek-r1-14b_baseline_2" => Box::new(deepseek_r1_14b_baseline_2::Bot::default()),
        "zoo/other/deepseek-r1-14b_market_maker" => Box::new(deepseek_r1_14b_market_maker::Bot::default()),
        "zoo/other/deepseek-r1-14b_market_maker_2" => Box::new(deepseek_r1_14b_market_maker_2::Bot::default()),
        "zoo/other/gemma4-26b_baseline" => Box::new(gemma4_26b_baseline::Bot::default()),
        "zoo/other/gemma4-26b_baseline_2" => Box::new(gemma4_26b_baseline_2::Bot::default()),
        "zoo/other/gemma4-26b_market_maker" => Box::new(gemma4_26b_market_maker::Bot::default()),
        "zoo/other/gemma4-26b_market_maker_2" => Box::new(gemma4_26b_market_maker_2::Bot::default()),
        "zoo/other/gpt-oss-120B_baseline" => Box::new(gpt_oss_120b_baseline::Baseline120::default()),
        "zoo/other/gpt-oss-120B_market_maker" => Box::new(gpt_oss_120b_market_maker::MarketMaker120::default()),
        "zoo/other/gpt-oss-20b_baseline" => Box::new(gpt_oss_20b_baseline::Baseline20::default()),
        "zoo/other/gpt-oss-20b_baseline_2" => Box::new(gpt_oss_20b_baseline_2::Baseline20Second::default()),
        "zoo/other/gpt-oss-20b_market_maker" => Box::new(gpt_oss_20b_market_maker::MarketMaker20::default()),
        "zoo/other/gpt-oss-20b_market_maker_2" => Box::new(gpt_oss_20b_market_maker_2::MarketMaker20Second::default()),
        "zoo/other/phi4-14b_baseline" => Box::new(phi4_14b_baseline::Baseline::default()),
        "zoo/other/phi4-14b_baseline_2" => Box::new(phi4_14b_baseline_2::Baseline2::default()),
        "zoo/other/phi4-14b_market_maker" => Box::new(phi4_14b_market_maker::MarketMaker::default()),
        "zoo/other/phi4-14b_market_maker_2" => Box::new(phi4_14b_market_maker_2::MarketMaker2::default()),
        "zoo/other/qwen3.8-27b-medium_baseline" => Box::new(qwen3_8_27b_medium_baseline::Baseline::default()),
        "zoo/other/qwen3.8-27b-medium_baseline_2" => Box::new(qwen3_8_27b_medium_baseline_2::Baseline2::default()),
        "zoo/other/qwen3.8-27b-medium_market_maker" => Box::new(qwen3_8_27b_medium_market_maker::MarketMaker::default()),
        "zoo/other/qwen3.8-27b-medium_market_maker_2" => Box::new(qwen3_8_27b_medium_market_maker_2::MarketMaker2::default()),
        _ => return None,
    })
}

/// The day's index of each named product (None: not on the day).
pub fn ids(day: &Day, names: &[&str]) -> Vec<Option<usize>> {
    names.iter().map(|n| day.product(n)).collect()
}

/// The index into `names` of a day's product, per product of the day.
pub fn lookup(day: &Day, names: &[&str]) -> Vec<Option<usize>> {
    day.products.iter().map(|p| names.iter().position(|n| n == p)).collect()
}

pub fn order(out: &mut Vec<Action>, product: usize, price: Price, quantity: i64) {
    out.push(Action::Order(Order { product, price, quantity, ioc: false }));
}

/// `max(depth.buy_orders)`: the best bid.
pub fn best_bid(book: &Book) -> Option<Price> {
    book.bids.iter().map(|l| l.0).max()
}

/// `min(depth.sell_orders)`: the best ask.
pub fn best_ask(book: &Book) -> Option<Price> {
    book.asks.iter().map(|l| l.0).min()
}

/// `max(depth.buy_orders.items(), key=lambda kv: (kv[1], -kv[0]))[0]`: the largest bid, the lowest price of equals.
pub fn bid_wall_low(book: &Book) -> Price {
    book.bids.iter().max_by_key(|l| (l.1, -l.0)).unwrap().0
}

/// `max(depth.sell_orders.items(), key=lambda kv: (-kv[1], kv[0]))[0]`: the largest ask, the highest price of equals.
pub fn ask_wall_high(book: &Book) -> Price {
    book.asks.iter().max_by_key(|l| (l.1, l.0)).unwrap().0
}

/// The book's bids sorted by price, highest first (`sorted(depth.buy_orders.items(), reverse=True)`).
pub fn bids_desc(book: &Book) -> Vec<(Price, i64)> {
    let mut v = book.bids.clone();
    v.sort_by(|a, b| b.0.cmp(&a.0));
    v
}

/// The book's asks sorted by price, lowest first, volumes positive (`sorted((p, -v) for p, v in depth.sell_orders.items())`).
pub fn asks_asc(book: &Book) -> Vec<(Price, i64)> {
    let mut v = book.asks.clone();
    v.sort_by(|a, b| a.0.cmp(&b.0));
    v
}
