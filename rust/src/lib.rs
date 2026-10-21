//! A Rust port of the Python engine (`arena/engine.py`) and one bot, kept apart from the Python
//! code so the two can be benchmarked like for like. See README.md.

pub mod bots;
pub mod dayfile;
pub mod engine;
pub mod json;
pub mod model;
pub mod py;
pub mod pyrandom;
mod sha512;
pub mod sim;
