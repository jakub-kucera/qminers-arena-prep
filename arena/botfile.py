"""Loads a single-file bot as a fresh module, the way a competition would run it."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType


class OverrideError(Exception):
    """A --set override doesn't match the bot."""


class BotFile:
    """A bot source file that can be loaded as a fresh module any number of times.

    provided_modules are made importable under the given names first (e.g. Prosperity's
    `datamodel`). In strict mode, a module-level STRICT flag is set to True so the bot raises
    errors instead of swallowing them. overrides set bot globals after loading
    (see parse_override).
    """

    def __init__(
        self,
        path: Path,
        provided_modules: dict[str, ModuleType],
        overrides: dict[str, object] | None = None,
        strict: bool = True,
    ):
        self.path = Path(path)
        self.provided_modules = provided_modules
        self.overrides = overrides or {}
        self.strict = strict
        self._code = compile(self.path.read_text(encoding="utf-8"), str(self.path), "exec")

    def load(self) -> ModuleType:
        sys.modules.update(self.provided_modules)
        name = f"arena_bot_{self.path.stem}"
        module = ModuleType(name)
        module.__file__ = str(self.path)
        # Registered before running so dataclasses and pickling inside the bot can find it.
        sys.modules[name] = module
        exec(self._code, module.__dict__)
        if self.strict and hasattr(module, "STRICT"):
            module.STRICT = True
        for target, value in self.overrides.items():
            _apply_override(module, target, value)
        return module


def parse_override(text: str) -> tuple[str, object]:
    """Parses `PATH=VALUE`, e.g. `PARAMS.KELP.make_edge=2`.

    PATH is a bot global followed by dict keys. VALUE is a Python literal; anything that isn't
    one (a bare word) is taken as a string.
    """
    target, sep, raw = text.partition("=")
    if not sep or not target.strip():
        raise ValueError(f"expected PATH=VALUE, got {text!r}")
    try:
        value = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        value = raw
    return target.strip(), value


def _apply_override(module: ModuleType, target: str, value: object) -> None:
    name, *keys = target.split(".")
    if not hasattr(module, name):
        raise OverrideError(f"--set {target}: the bot has no global named {name!r}")
    if not keys:
        setattr(module, name, value)
        return
    container = getattr(module, name)
    for key in keys[:-1]:
        if key not in container:
            raise OverrideError(f"--set {target}: {key!r} not found")
        container = container[key]
    container[keys[-1]] = value
