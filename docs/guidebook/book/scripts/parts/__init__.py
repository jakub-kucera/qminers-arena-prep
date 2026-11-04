"""The guidebook's data steps and figures, one pair of modules a part, so the parts never edit the same file.

data_<part>.py defines STEPS = {name: function} and imports its helpers from make_data (run, write, number, total,
grid_table, p3_day, wall_mid, TEMPLATE, ROOT); figures_<part>.py defines FIGURES = [function, ...] and imports from
make_figures (read, save, box, arrow, canvas, thousands, T and the colours). make_data.py and make_figures.py find
them; `--only NAME` runs one.
"""
