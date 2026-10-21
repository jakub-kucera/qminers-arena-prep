//! bots/zoo/other/deepseek-r1-14b_baseline.py
//!
//! It never imports `Order`, so the first tick it decides to trade raises NameError: no orders
//! reach the engine, and traderData keeps its last value (the bot re-reads it every tick).

use super::py;
use super::{best_ask, best_bid};
use crate::arena::engine::TickView;
use crate::arena::model::{Action, Day, Fill, MarketTrade, OpenOrder};

const MA_WINDOW: usize = 200;

#[derive(Default)]
pub struct Bot {
    saved: Vec<Option<Vec<f64>>>, // traderData: each product's price_history
    error: Option<String>,
}

impl crate::arena::engine::Bot for Bot {
    fn begin_day(&mut self, day: &Day, _names: &[String]) {
        self.saved = vec![None; day.products.len()];
    }

    fn failed(&mut self) -> Option<String> {
        self.error.take()
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _: &[Fill], _: &[Vec<MarketTrade>], _: &[OpenOrder], _out: &mut Vec<Action>) {
        let mut state = self.saved.clone();
        for &product in tick.order {
            let book = tick.books[product].as_ref().unwrap();
            let position = positions[product];
            let (bb, ba) = (best_bid(book), best_ask(book));
            let mid = match (bb, ba) {
                (Some(b), Some(a)) => Some((b + a) as f64 / 2.0),
                _ => None,
            };
            let history = state[product].get_or_insert_with(Vec::new);
            if let Some(mid) = mid {
                history.push(mid);
                if history.len() > MA_WINDOW {
                    history.remove(0);
                }
            }
            let ma = (!history.is_empty()).then(|| py::sum(history.iter().copied()) / history.len() as f64);
            if let (Some(ma), Some(mid)) = (ma, mid) {
                let wants = (mid > ma && position < 50 && ba.is_some()) || (mid < ma && position > -50 && bb.is_some());
                if wants {
                    self.error = Some("NameError: name 'Order' is not defined. Did you mean: 'orders'?".into()); // Order(...) with Order undefined
                    return;
                }
            }
        }
        self.saved = state;
    }
}
