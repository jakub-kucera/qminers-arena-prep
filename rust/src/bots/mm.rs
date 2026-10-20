//! bots/mm.py in Rust: keep the two equal, experiments/rust_bench.py checks that they trade the same.
//!
//! A plain market maker on each of its products, in order. Fair is the wall mid. It takes (IOC)
//! every level at least `take_edge` through fair, then quotes the rest of its room one tick inside
//! the best, but no closer to fair than `make_edge`. Resting orders are cancelled, except with
//! `hold`: those already at the quote's price are kept (oldest first, while they fit its room).

use crate::engine::{Bot, TickView};
use crate::model::{wall, Action, Book, Day, Fill, MarketTrade, OpenOrder, Order};

pub const LIMIT: i64 = 50;

#[derive(Clone)]
pub struct Params {
    pub product: String,
    pub make_edge: f64,
    pub take_edge: f64,
    pub hold: bool,
}

pub struct MarketMaker {
    params: Vec<Params>,
    ids: Vec<usize>,
}

impl MarketMaker {
    pub fn new(params: Vec<Params>) -> Self {
        MarketMaker { params, ids: Vec::new() }
    }
}

impl Bot for MarketMaker {
    fn begin_day(&mut self, day: &Day) {
        self.ids = self.params.iter().map(|p| day.product(&p.product).unwrap_or(usize::MAX)).collect();
    }

    fn step(&mut self, tick: &TickView, positions: &[i64], _own_fills: &[Fill], _market_trades: &[Vec<MarketTrade>], open_orders: &[OpenOrder], actions: &mut Vec<Action>) {
        for (params, &product) in self.params.iter().zip(&self.ids) {
            let resting = open_orders.iter().filter(|o| o.product == product);
            match tick.books.get(product).and_then(|b| b.as_ref()) {
                Some(book) if !book.bids.is_empty() && !book.asks.is_empty() => quote(product, params, book, positions[product], resting, actions),
                _ => actions.extend(resting.map(|o| Action::Cancel(o.id))),
            }
        }
    }
}

fn quote<'a>(product: usize, params: &Params, book: &Book, position: i64, resting: impl Iterator<Item = &'a OpenOrder>, actions: &mut Vec<Action>) {
    let (bids, asks) = (&book.bids, &book.asks);
    let fair = (wall(bids) + wall(asks)) as f64 / 2.0;
    // The takes: every level at least take_edge through fair, while the room lasts.
    let takes = |levels: &[(i64, i64)], room: i64, through: &dyn Fn(i64) -> bool| -> (usize, i64) {
        let (mut count, mut left) = (0, room);
        for &(price, volume) in levels {
            if !through(price) || left == 0 {
                break;
            }
            left -= volume.min(left);
            count += 1;
        }
        (count, left)
    };
    let (buys, buy_room) = takes(asks, LIMIT - position, &|price| price as f64 <= fair - params.take_edge);
    let (sells, sell_room) = takes(bids, LIMIT + position, &|price| price as f64 >= fair + params.take_edge);
    let bid = (bids[0].0 + 1).min((fair - params.make_edge).floor() as i64);
    let ask = (asks[0].0 - 1).max((fair + params.make_edge).ceil() as i64);
    let (mut kept_buys, mut kept_sells) = (0, 0);
    for order in resting {
        if params.hold && order.quantity > 0 && order.price == bid && kept_buys + order.quantity <= buy_room {
            kept_buys += order.quantity;
        } else if params.hold && order.quantity < 0 && order.price == ask && kept_sells - order.quantity <= sell_room {
            kept_sells -= order.quantity;
        } else {
            actions.push(Action::Cancel(order.id));
        }
    }
    let mut room = LIMIT - position;
    for &(price, volume) in &asks[..buys] {
        let quantity = volume.min(room);
        actions.push(Action::Order(Order { product, price, quantity, ioc: true }));
        room -= quantity;
    }
    let mut room = LIMIT + position;
    for &(price, volume) in &bids[..sells] {
        let quantity = volume.min(room);
        actions.push(Action::Order(Order { product, price, quantity: -quantity, ioc: true }));
        room -= quantity;
    }
    if buy_room > kept_buys {
        actions.push(Action::Order(Order { product, price: bid, quantity: buy_room - kept_buys, ioc: false }));
    }
    if sell_room > kept_sells {
        actions.push(Action::Order(Order { product, price: ask, quantity: kept_sells - sell_room, ioc: false }));
    }
}
