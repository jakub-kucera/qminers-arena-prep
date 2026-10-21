//! The Rust port, laid out as python/ is: each twin at its Python file's path (arena/engine.rs for
//! python/arena/engine.py, bots/template.rs for python/bots/template.py), the Rust-only pieces in
//! support/, the command line in main.rs and commands/. See README.md.

pub mod arena;
pub mod bots;
pub mod support;
