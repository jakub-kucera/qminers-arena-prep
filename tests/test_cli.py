from pathlib import Path

from arena import backtest
from arena.cli import participant_names
from tests.test_grid import BOT


def test_participant_names_number_repeated_files():
    names = participant_names(Path("bots/template.py"), [Path("x/template.py"), Path("other.py"), Path("template.py")])
    assert names == ["template", "template#2", "other", "template#3"]


def test_backtest_reports_rivals(capsys, tmp_path, data_dir):
    path = tmp_path / "bot.py"
    path.write_text(BOT)
    code = backtest.main([str(path), "1", "--data", str(data_dir), "--vs", str(path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "vs bot#2: pnl" in out
    assert "rivals: bot#2" in out
