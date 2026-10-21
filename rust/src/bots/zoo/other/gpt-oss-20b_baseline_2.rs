//! python/bots/zoo/other/gpt-oss-20b_baseline_2.py

use crate::arena::engine::TickView;
use crate::arena::model::{Action, Fill, MarketTrade, OpenOrder};

/// gpt-oss-20b_baseline_2.py: it stores the mid before reading the last one, so the move it trades
/// on is always 0 and it never trades. Its json.loads has no guard, but it only ever reads its own output.
#[derive(Default)]
pub struct Baseline20Second;

impl crate::arena::engine::Bot for Baseline20Second {
    fn step(&mut self, _: &TickView, _: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], _: &mut Vec<Action>) {}
}
