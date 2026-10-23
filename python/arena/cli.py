"""Command-line options shared by arena.backtest, arena.validate, arena.grid, arena.compare and arena.stress."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from arena.botfile import parse_override
from arena.engine import DayResult, EngineConfig, QueueModel, TradeMatching, run_market
from arena.formats import FORMATS
from arena.model import Cancel, Day


@dataclass
class Setup:
    format: ModuleType
    days: list[Day]
    config: EngineConfig
    overrides: dict[str, object]
    rivals: list[Path] = field(default_factory=list)  # bots trading in the same market (--vs)
    requote: bool = False  # the rivals cancel all their resting orders every tick (--requote)
    engine: str = "python"  # --engine: "rust" runs the backtests on rust/ (python/arena/rust.py)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("bot", type=Path, help="bot file")
    parser.add_argument("days", nargs="+", help="days to replay: ROUND for all its days, or ROUND-DAY (e.g. 1, 1-0, 1--1)")
    parser.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="competition format (default: prosperity)")
    parser.add_argument("--data", default="p3", help="data folder, or p2 / p3 / p4 for the Prosperity data in references/ (default: p3)")
    parser.add_argument(
        "--match-trades",
        type=TradeMatching,
        choices=list(TradeMatching),
        default=TradeMatching.ALL,
        help="which market trades leftover orders can fill against: at the order's price or worse (all), "
        "strictly worse (worse), or none (default: all)",
    )
    parser.add_argument(
        "--resting",
        action="store_true",
        help="unfilled orders rest on the book until filled or cancelled, with a queue model "
        "(default: they're cancelled at the end of each tick, as in Prosperity; always on for a format whose orders rest)",
    )
    parser.add_argument(
        "--queue",
        type=QueueModel,
        choices=list(QueueModel),
        default=QueueModel.BACK,
        help="with --resting, where other orders' cancellations at your price fall: always behind you (back), "
        "split by your place in the queue (prob, see --queue-power), or everyone re-posts behind you every tick "
        "(front) (default: back)",
    )
    parser.add_argument(
        "--queue-power",
        type=float,
        default=1.0,
        help="--queue prob: a cancellation lands ahead of you with probability x**N, x your share of the queue "
        "ahead; 1 is uniform, a large N tends to back (default: 1)",
    )
    parser.add_argument(
        "--fill-ratio",
        type=float,
        default=1.0,
        help="share of book and market-trade volume available to you; below 1 approximates other teams "
        "competing for the same fills (default: 1)",
    )
    parser.add_argument("--seed", type=int, default=0, help="seed for --fill-ratio draws (default: 0)")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="PATH=VALUE",
        help="override a bot global, e.g. --set PARAMS.KELP.make_edge=2 (repeatable)",
    )


def add_rival_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--vs",
        dest="rivals",
        type=Path,
        action="append",
        default=[],
        metavar="BOT",
        help="another bot trading in the same market: it competes for the same fills and can trade with yours. "
        "Repeatable; give a file twice for two copies. --set only applies to your bot.",
    )
    parser.add_argument(
        "--requote",
        action="store_true",
        help="the rivals cancel all their resting orders before every tick, as bots written for orders that live one "
        "tick (Prosperity's) expect; use it with --resting",
    )


def add_engine_argument(parser: argparse.ArgumentParser, help: str | None = None) -> None:
    """--engine, and --allow-stale for a Rust twin checked against older Python code (python/arena/rust.py `prepare`)."""
    parser.add_argument("--engine", choices=["python", "rust"], default="python",
                        help=help or "run the backtests on our engine, or on its Rust port (rust/: needs cargo, and bots with a Rust twin, "
                        "rust/twins.json), with the same results about 100 times faster (default: python)")
    parser.add_argument("--allow-stale", action="store_true",
                        help="with --engine rust, run even if a twin's Python code changed since its Rust port was checked: Rust then "
                        "runs the old code (default: refuse)")


def setup(args: argparse.Namespace) -> Setup:
    fmt = FORMATS[args.format]
    days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    config = EngineConfig(
        trade_matching=args.match_trades,
        resting=args.resting or getattr(fmt, "RESTING", False),  # a format whose orders rest runs that way
        queue=args.queue,
        queue_power=args.queue_power,
        fill_ratio=args.fill_ratio,
        seed=args.seed,
    )
    overrides = dict(parse_override(text) for text in args.overrides)
    return Setup(fmt, days, config, overrides, getattr(args, "rivals", []), getattr(args, "requote", False), getattr(args, "engine", "python"))


def participant_names(bot: Path, rivals: list) -> list[str]:
    """File stems, numbered from the second copy on: template, template#2, other. A rival is a path or
    an arena.scenario.Rival (a file with overrides)."""
    seen: Counter[str] = Counter()
    names = []
    for path in [bot, *(getattr(r, "path", r) for r in rivals)]:
        seen[path.stem] += 1
        names.append(path.stem if seen[path.stem] == 1 else f"{path.stem}#{seen[path.stem]}")
    return names


def participants(bot: Path, overrides: dict[str, object], rivals: list[Path], requote: bool = False) -> list[tuple[str, Path, dict, bool]]:
    """(name, file, overrides, requote) for the bot and its rivals, as python/arena/rust.py takes them."""
    names = participant_names(bot, rivals)
    return [(names[0], bot, overrides, False)] + [(name, path, {}, requote) for name, path in zip(names[1:], rivals)]


def backtest_days(data: str, specs: list[str], engine: str = "python", format_name: str = "prosperity") -> list:
    """The days the specs select, for backtests through `backtest` only: Python Days, or with engine
    "rust" and Prosperity data, references to their CSVs that Rust reads itself (nothing loaded here).
    A day in another format is loaded here, and Rust gets it exported once per process."""
    fmt = FORMATS[format_name]
    if engine == "rust" and format_name == "prosperity":
        from arena import rust

        return rust.prosperity_days(data, specs)
    return fmt.load_days(fmt.resolve_data_dir(data), specs)


def backtest(day: Day, bots: list[tuple[str, Path, dict, bool]], config: EngineConfig, engine: str = "python", strict: bool = False,
             fields: tuple[str, ...] | None = None, format_name: str = "prosperity") -> list[DayResult]:
    """The (name, bot file, overrides, requote) participants in one market on one day, in the format
    (Prosperity's by default), on either engine: each one's DayResult. With engine "rust" the day may
    be a day file (arena.rust.sim_day_file), `fields` limits what is read back, and `strict` is moot
    (a Rust twin can't raise from a bug)."""
    if engine == "rust":
        from arena import rust

        return rust.backtest(day, bots, config, fields)
    fmt = FORMATS[format_name]
    loaded = [(name, fmt.load_bot(path, overrides, strict)) for name, path, overrides, _ in bots]
    return run_market(day, [(name, Requote(bot) if requote else bot) for (name, bot), (*_, requote) in zip(loaded, bots)], config)


# ---------------------------------------------------------------------------- the day's data, for the experiments

TEMPLATE = Path("python/bots/template.py")
TEMPLATES = {"prosperity": TEMPLATE, "drill": Path("python/bots/drill/template.py")}  # the default --bot per format


def add_dataset_arguments(parser: argparse.ArgumentParser, products: bool = True, bot: bool = True) -> None:
    """--data, --days, --format, --bot and --products: one dataset in place of an experiment's
    built-in Prosperity ones, so it runs on the day's download (dataset_from reads them). Without
    --data the experiment runs as it always has, so the results it gave stay reproducible."""
    group = parser.add_argument_group("the day's data", "one dataset in place of the experiment's built-in Prosperity ones, "
                                      "e.g. --data data/arena --days 1 2 --format qminers --bot python/bots/qminers/template.py")
    group.add_argument("--data", help="a data folder, or p2 / p3 / p4")
    group.add_argument("--days", nargs="+", help="day specs as arena.backtest takes them (required with --data), e.g. 1 2, or all for drill sessions")
    group.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="the data's format (default: prosperity)")
    if bot:
        group.add_argument("--bot", type=Path, help="the template file to run, written for that format (default: "
                           + ", ".join(f"{path} for {name}" for name, path in TEMPLATES.items()) + ")")
    if products:
        group.add_argument("--products", help="comma-separated products to study (default: every product in the data"
                           + (" that the bot's PARAMS lists)" if bot else ")"))


@dataclass(frozen=True)
class Dataset:
    """The dataset add_dataset_arguments names: where it is, which days, its format, the bot and the products."""

    name: str  # as the experiment's tables show it
    data: str
    days: tuple[str, ...]
    format: str = "prosperity"
    bot: str = str(TEMPLATE)
    products: tuple[str, ...] = ()


def dataset_from(args: argparse.Namespace) -> Dataset | None:
    """The dataset the arguments name, or None when there is no --data (the experiment's own). A
    ValueError for options that need --data, or --data without --days."""
    bot = getattr(args, "bot", None)
    if args.data is None:
        if args.format != "prosperity" or bot is not None or args.days or getattr(args, "products", None):
            raise ValueError("--days, --format, --bot and --products choose the day's data: give --data too")
        return None
    if not args.days:
        raise ValueError("--data needs --days, e.g. --days 1 2 (Prosperity rounds) or --days all (drill sessions)")
    fmt = FORMATS[args.format]
    bot = str(bot or TEMPLATES.get(args.format, TEMPLATE))
    if getattr(args, "products", None):
        products = tuple(p.strip() for p in args.products.split(",") if p.strip())
    else:
        days = fmt.load_days(fmt.resolve_data_dir(args.data), list(args.days))
        products = sorted({p for day in days for p in day.products})
        if hasattr(args, "bot"):
            listed = bot_params(bot, args.format)
            products = [p for p in products if p in listed]
        products = tuple(products)
    return Dataset(f"{Path(args.data).name or args.data} {' '.join(args.days)}", args.data, tuple(args.days), args.format, bot, products)


def bot_module(path: str | Path, format_name: str):
    """The bot file loaded as a module under its format (with that format's provided modules)."""
    FORMATS[format_name].load_bot(Path(path), {}, strict=False)
    return sys.modules[f"arena_bot_{Path(path).stem}"]  # BotFile.load registers the module under this name


def bot_params(path: str | Path, format_name: str) -> dict:
    """The bot file's PARAMS, as it loads under its format ({} if it has none)."""
    params = getattr(bot_module(path, format_name), "PARAMS", None)
    return params if isinstance(params, dict) else {}


def run_with_rivals(
    fmt,
    day: Day,
    bot: Path,
    overrides: dict[str, object],
    rivals: list,
    config: EngineConfig,
    strict: bool = True,
    requote: bool = False,
) -> list[DayResult]:
    """Runs the bot, plus any rivals in the same market (paths, or arena.scenario.Rivals with their
    overrides). The bot's result comes first."""
    others = [fmt.load_bot(getattr(rival, "path", rival), getattr(rival, "overrides", {}), strict) for rival in rivals]
    if requote:
        others = [Requote(other) for other in others]
    bots = [fmt.load_bot(bot, overrides, strict), *others]
    return run_market(day, list(zip(participant_names(bot, rivals), bots)), config)


class Requote:
    """Cancels all of a bot's resting orders before each tick, and hides them from it.

    Bots written for orders that live one tick (Prosperity's) never cancel: under --resting their
    orders pile up until the limit check rejects everything. Wrapped, each tick's orders replace
    the last tick's, which is how they were meant to run, though they keep their queue place only
    for that tick.
    """

    def __init__(self, bot):
        self.bot = bot

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        actions = self.bot.step(tick, positions, own_fills, market_trades, [])
        return [Cancel(order.id) for order in open_orders] + [a for a in actions if not isinstance(a, Cancel)]
