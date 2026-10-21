//! python/arena/model.py's types. Products are indices into `Day::products`, which is sorted by name (the
//! order the Python engine sorts them in wherever order matters); trader names are indices into
//! `Day::names`, 0 being the empty name.

pub type Price = i64;
pub type Name = u32;

#[derive(Clone, Debug, Default, PartialEq)]
pub struct Book {
    pub bids: Vec<(Price, i64)>, // (price, volume), best first
    pub asks: Vec<(Price, i64)>,
}

impl Book {
    pub fn mid(&self) -> Option<f64> {
        match (self.bids.first(), self.asks.first()) {
            (Some(b), Some(a)) => Some((b.0 + a.0) as f64 / 2.0),
            _ => None,
        }
    }

    /// The largest level each side, ties to the level nearer the touch.
    pub fn wall_mid(&self) -> Option<f64> {
        if self.bids.is_empty() || self.asks.is_empty() {
            return None;
        }
        Some((wall(&self.bids) + wall(&self.asks)) as f64 / 2.0)
    }
}

pub fn wall(levels: &[(Price, i64)]) -> Price {
    let mut best = levels[0];
    for &level in &levels[1..] {
        if level.1 > best.1 {
            best = level;
        }
    }
    best.0
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct MarketTrade {
    pub product: usize,
    pub price: Price,
    pub quantity: i64,
    pub buyer: Name,
    pub seller: Name,
    pub timestamp: i64,
}

pub struct Tick {
    pub timestamp: i64,
    pub books: Vec<Option<Book>>,         // per product; None: no book this tick
    pub order: Vec<usize>,                // the products with a book, in the Python day's dict order
    pub trades: Vec<Vec<MarketTrade>>,    // per product
    pub marks: Vec<Option<f64>>,          // per product; None: fall back to the book mid
}

pub struct Day {
    pub name: String,
    pub products: Vec<String>,
    pub limits: Vec<i64>,
    pub order: Vec<usize>, // the products in the Python day's order (its `products` list)
    pub limits_order: Vec<usize>, // the products in its `limits` dict's order (a drill bot's api.symbols())
    pub info: Vec<Option<(f64, f64)>>, // per product, Day.info's (tick, unit), from a format with decimal prices
    pub ticks: Vec<Tick>,
    pub names: Vec<String>,
}

impl Day {
    pub fn product(&self, name: &str) -> Option<usize> {
        self.products.iter().position(|p| p == name)
    }
}

#[derive(Clone, Copy, Debug)]
pub struct Order {
    pub product: usize,
    pub price: Price,
    pub quantity: i64,
    pub ioc: bool,
}

#[derive(Clone, Copy, Debug)]
pub enum Action {
    Order(Order),
    Cancel(u64),
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct OpenOrder {
    pub id: u64,
    pub product: usize,
    pub price: Price,
    pub quantity: i64,
    pub timestamp: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Source {
    Book,
    Trade,
    Cross,
}

impl Source {
    pub fn as_str(self) -> &'static str {
        match self {
            Source::Book => "book",
            Source::Trade => "trade",
            Source::Cross => "cross",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Fill {
    pub timestamp: i64,
    pub product: usize,
    pub price: Price,
    pub quantity: i64,
    pub source: Source,
    pub counterparty: Name,
    pub order_id: u64,
}
