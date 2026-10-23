//! python/bots/drill/template.py in Rust: the template's STRATEGY and EXECUTION (python/bots/template.rs,
//! whose child module this is) behind the drill format's ADAPTER, `Adapter::DRILL`: prices in each
//! product's ticks, converted from and to the format's price units as its plug-in and ADAPTER do
//! (python/arena/formats/drill.py), products in the exchange's order, trades without names, and each
//! product's limit from the exchange. The step itself is the template's, for every adapter.

use super::*;

/// The price-unit conversion of an adapter with `units` (the drill's ADAPTER): per product of the day.
#[derive(Default)]
pub(super) struct Drill {
    pub(super) tick: Vec<f64>,           // api.tick_size, from Day.info (the plug-in's default 0.01)
    pub(super) unit: Vec<f64>,           // the price unit the engine counts in (default 0.01)
    pub(super) books: Vec<Option<Book>>, // this tick's books in ticks (read_book), None when empty
}

impl Drill {
    /// The api's price of a price in units (`_px`), in ticks (`to_ticks`).
    pub(super) fn ticks(&self, k: usize, units: Price) -> Price {
        round(crate::support::py::round_to(units as f64 * self.unit[k], 10) / self.tick[k])
    }

    /// The price an order in ticks is sent at (`to_price`), in the engine's units (`_units`).
    pub(super) fn units(&self, k: usize, ticks: Price) -> Price {
        let units = crate::support::py::round_to(ticks as f64 * self.tick[k], 10) / self.unit[k];
        debug_assert!((units - units.round_ties_even()).abs() <= 1e-6, "a whole number of ticks is on the grid");
        round(units)
    }
}

impl Template {
    /// python/bots/drill/template.py: the same settings, behind the drill format's ADAPTER.
    pub fn drill(globals: &Value) -> Result<Template, String> {
        Ok(Template::from_globals(globals)?.with_adapter(Adapter::DRILL))
    }
}
