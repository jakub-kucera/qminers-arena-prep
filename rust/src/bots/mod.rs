//! Bots written in Rust. Each one has a Python twin under bots/ that must trade the same; the
//! registry of twins is rust/twins.json, and arena/rust.py passes each bot its Python file's
//! globals (as JSON) so `--set` overrides reach it.

pub mod mm;
pub mod rivals;
pub mod template;
pub mod zoo;

use crate::engine::{Bot, TickView};
use crate::json::Value;
use crate::model::{Action, Day, Fill, MarketTrade, OpenOrder};

/// A bot by its kind (rust/twins.json), built from its Python twin's globals.
pub fn build(kind: &str, globals: &Value) -> Result<Box<dyn Bot + Send>, String> {
    Ok(match kind {
        "mm" => Box::new(mm::MarketMaker::from_globals(globals)?),
        "template" => Box::new(template::Template::from_globals(globals)?),
        "sniper" => Box::new(rivals::Sniper::from_globals(globals)?),
        "spoofer" => Box::new(rivals::Spoofer::from_globals(globals)?),
        "trapper" => Box::new(rivals::Trapper::from_globals(globals)?),
        other => match zoo::build(other) {
            Some(bot) => bot,
            None => return Err(format!("no Rust bot of kind {other:?}")),
        },
    })
}

/// arena.cli.Requote: cancels all of a bot's resting orders before each tick, and hides them from it.
pub struct Requote {
    inner: Box<dyn Bot + Send>,
    actions: Vec<Action>,
}

impl Requote {
    pub fn new(inner: Box<dyn Bot + Send>) -> Self {
        Requote { inner, actions: Vec::new() }
    }
}

impl Bot for Requote {
    fn begin_day(&mut self, day: &Day, names: &[String]) {
        self.inner.begin_day(day, names);
    }

    fn failed(&mut self) -> Option<String> {
        self.inner.failed()
    }

    fn product_name(&self, product: usize) -> Option<String> {
        self.inner.product_name(product)
    }

    fn memory(&self, day: &Day) -> Option<String> {
        self.inner.memory(day)
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], own_fills: &[Fill], market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        self.actions.clear();
        self.inner.step(tick, positions, own_fills, market_trades, &[], &mut self.actions);
        out.extend(open_orders.iter().map(|o| Action::Cancel(o.id)));
        out.extend(self.actions.iter().filter(|a| matches!(a, Action::Order(_))));
    }
}
