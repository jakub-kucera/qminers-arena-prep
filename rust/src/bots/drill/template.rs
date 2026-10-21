//! python/bots/drill/template.py in Rust: the template's STRATEGY and EXECUTION (python/bots/template.rs,
//! whose child module this is) behind the drill format's ADAPTER: prices in each product's ticks,
//! converted from and to the format's price units as its plug-in and ADAPTER do
//! (python/arena/formats/drill.py), products in the exchange's order, trades without names, and
//! each product's limit from the exchange.

use super::*;

/// The drill format's ADAPTER (python/bots/drill/template.py): what it converts, per product of the day.
#[derive(Default)]
pub(super) struct Drill {
    pub(super) tick: Vec<f64>,           // api.tick_size, from Day.info (the plug-in's default 0.01)
    pub(super) unit: Vec<f64>,           // the price unit the engine counts in (default 0.01)
    pub(super) books: Vec<Option<Book>>, // this tick's books in ticks (read_book), None when empty
}

impl Drill {
    /// The api's price of a price in units (`_px`), in ticks (`to_ticks`).
    fn ticks(&self, k: usize, units: Price) -> Price {
        round(crate::support::py::round_to(units as f64 * self.unit[k], 10) / self.tick[k])
    }

    /// The price an order in ticks is sent at (`to_price`), in the engine's units (`_units`).
    fn units(&self, k: usize, ticks: Price) -> Price {
        let units = crate::support::py::round_to(ticks as f64 * self.tick[k], 10) / self.unit[k];
        debug_assert!((units - units.round_ties_even()).abs() <= 1e-6, "a whole number of ticks is on the grid");
        round(units)
    }
}

impl Template {
    /// python/bots/drill/template.py: the same settings, behind the drill format's ADAPTER.
    pub fn drill(globals: &Value) -> Result<Template, String> {
        Ok(Template { drill: Some(Drill::default()), ..Template::from_globals(globals)? })
    }

    /// The drill ADAPTER's step: Bot.on_tick.
    pub(super) fn drill_step(&mut self, tick: &TickView, positions: &[i64], own_fills: &[Fill], market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], out: &mut Vec<Action>) {
        let d = self.drill.as_mut().unwrap();
        for (k, book) in tick.books.iter().enumerate() {
            d.books[k] = book.as_ref().filter(|b| !b.bids.is_empty() || !b.asks.is_empty()).map(|b| {
                let side = |levels: &[(Price, i64)]| levels.iter().map(|&(price, volume)| (d.ticks(k, price), volume)).collect();
                Book { bids: side(&b.bids), asks: side(&b.asks) }
            });
        }
        // read_trades: (buyer, seller, quantity) with no names; read_fills: our fills as (price in ticks, signed quantity)
        for (k, list) in self.trades.iter_mut().enumerate() {
            list.clear();
            list.extend(market_trades[k].iter().map(|t| (0, 0, t.quantity)));
            self.fills[k].clear();
        }
        for f in own_fills {
            self.fills[f.product].push((d.ticks(f.product, f.price), f.quantity));
        }
        // api.symbols() that have a book, those that follow or hedge another last
        self.order.clear();
        self.order.extend(self.symbols.iter().copied().filter(|&k| d.books[k].is_some()));
        let depends = &self.depends;
        self.order.sort_by_key(|&k| depends[k]);
        for plan in self.plans.iter_mut() {
            *plan = None;
        }
        self.plan_order.clear();
        for i in 0..self.order.len() {
            let product = self.order[i];
            let Some(p) = self.params[product].as_ref() else { continue };
            let market = Market {
                books: &d.books,
                trades: &self.trades[product],
                fills: &self.fills[product],
                timestamp: tick.timestamp,
                plans: &self.plans,
                plan_order: &self.plan_order,
                weights: &self.weights[product],
            };
            let plan = trade_product(product, d.books[product].as_ref().unwrap(), positions[product], p, &mut self.memory[product], &market);
            // read_resting: api.orders(product), oldest first as the engine keeps them
            let resting: Vec<(u64, Price, i64)> = open_orders.iter().filter(|o| o.product == product).map(|o| (o.id, d.ticks(product, o.price), o.quantity)).collect();
            let start = out.len();
            execute(product, &plan, &resting, out);
            for action in &mut out[start..] {
                if let Action::Order(order) = action {
                    order.price = d.units(product, order.price);
                }
            }
            self.plans[product] = Some(plan);
            self.plan_order.push(product);
        }
    }
}
