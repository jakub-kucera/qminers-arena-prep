"""Competition formats: the only code that knows a competition's data files and bot API.

Each format module provides:

    PROVIDED_MODULES: set[str]
        Modules the competition makes importable for bots (e.g. "datamodel").
    resolve_data_dir(arg: str) -> Path
        Turns the --data argument into a folder.
    load_days(data_dir: Path, specs: list[str]) -> list[Day]
        Loads the requested days into engine types.
    load_bot(path, overrides, strict, fresh_each_tick=False) -> engine.Bot
        Wraps a bot file so the engine can call it. With fresh_each_tick the bot file is
        reloaded every tick, which shows whether it keeps state outside the competition's
        official state mechanism.
    check_source(tree: ast.Module) -> list[str]
        Problems with the bot's entry point (empty list if fine).

Optional:

    RESTING: bool
        True if the competition's orders rest until cancelled; the tools then run as with
        --resting.

The Arena's format is qminers.py, already registered as `--format qminers`: a day-of skeleton (a copy
of snapshots.py with TODO(day) markers) to fill in on the day, by ON_THE_DAY.md, "The format swap,
step by step". Its loader and its wrapper are replaced separately, each from the nearest shape:
snapshots.py (book snapshots in CSV, a bot answering a state with orders), orderlog.py (an
order-by-order event log, with the drill's bot API) or drill.py (book changes, a callback API,
decimal prices, orders that rest; the differences from Prosperity marked).
"""

from types import ModuleType

from arena.formats import drill, orderlog, prosperity, qminers, snapshots

FORMATS: dict[str, ModuleType] = {"prosperity": prosperity, "drill": drill, "snapshots": snapshots, "orderlog": orderlog,
                              "qminers": qminers}
