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

To support a new competition, copy drill.py (a format deliberately unlike Prosperity's, with
the differences marked) and rewrite it for the new format.
"""

from types import ModuleType

from arena.formats import drill, prosperity

FORMATS: dict[str, ModuleType] = {"prosperity": prosperity, "drill": drill}
