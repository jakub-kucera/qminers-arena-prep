---
title: Hummingbot's Avellaneda–Stoikov guide and technical deep dive
type: source
repo: online-snapshots
status: read
updated: 2026-10-13
---

# Hummingbot, "Guide to the Avellaneda & Stoikov Strategy" and "Technical Deep Dive into the Avellaneda & Stoikov Strategy" (blog posts)

## What it is
Two posts by the Hummingbot team (an open-source crypto market-making bot) on its `avellaneda_market_making` strategy: a plain guide (`online-snapshots/hummingbot-as-guide.md`) and a deep dive into how it sets the model's parameters (`online-snapshots/hummingbot-as-deep-dive.md`). Both were saved on 2026-10-13 from the pages' static HTML; the guide's formulas are images, so the snapshot's header transcribes them as read on the page images. The pages print in dark mode, and Marker dropped most of their text, so they are not in `literature_md/`.

## Layout and code map
- **The model** (`online-snapshots/hummingbot-as-deep-dive.md:18-30`): `r(s, q, t, σ) = s − qγσ²(T − t)` and `δ^a + δ^b = γσ²(T − t) + (2/γ)·ln(1 + γ/κ)`, the published A–S eqs. 29–30 *(checked against [Avellaneda–Stoikov](hft-in-a-limit-order-book.md))*. The guide shows the same two formulas as images (`online-snapshots/hummingbot-as-guide.md:1`).
- **Quotes** (guide): bid = `r − spread/2`, ask = `r + spread/2`; `q` is the distance from a target inventory share; `T` is a session length that restarts, since crypto never closes.
- **γ from the user's spread band** (`online-snapshots/hummingbot-as-deep-dive.md:76-118`): requiring the optimal ask at t = 0 to be at least `min_spread` and the bid at most `max_spread` gives `γ ≤ (max_spread − min_spread)/(2|q|σ²) = γ_max`, and `γ = γ_max · IRA` with `inventory_risk_aversion` in (0, 1).
- **κ from the widest spread** (`online-snapshots/hummingbot-as-deep-dive.md:122-136`): `(δ^a + δ^b)_max = (2 − IRA)·max_spread + IRA·min_spread`, and `κ = γ / (exp{((δ^a + δ^b)γ − σ²γ²)/2} − 1)`, which is eq. 30 at t = 0, T = 1 solved for κ *(checked by algebra)*.
- **Order size** (`online-snapshots/hummingbot-as-deep-dive.md:140-144`): `η = IRA / total inventory`, after Fushimi et al. 2018.
- **γ → 0** (`online-snapshots/hummingbot-as-deep-dive.md:148-165`): the quotes centre on the mid and the spread tends to `2/κ`, which they read as plain market making being a special case.

## What carries over
- **Nobody estimates γ and κ from the book here either.** They are backed out of a spread band the user chooses, so the "model" is a parametrised skew and spread. That is what our `skew` and `make_edge` already are ([optimal quoting models](../concepts/optimal-quoting-models.md)).
- **As written, the skew does not grow with inventory** *(inferred from the formulas, the code was not read)*: with `γ = γ_max · IRA` and `γ_max ∝ 1/|q|`, the reservation shift `qγσ²` at t = 0 is `sign(q) · IRA · (max_spread − min_spread)/2` for every nonzero `q`. That holds only if γ is recomputed with the current `q`; the posts recompute parameters on volatility changes.

## Traps
- **The per-side inequalities have `(1/2)·ln(1 + γ/κ)`** (`online-snapshots/hummingbot-as-deep-dive.md:87-91`) where A–S's half-spread term is `(1/γ)·ln(1 + γ/κ)`. It cancels in the difference, so `γ_max` is unaffected.
- **A stray formula:** `ker f = {g ∈ G : f(g) = e_H}` (`online-snapshots/hummingbot-as-deep-dive.md:22-24`), a group-theory example left in the page.
- **The references say "Avellaneda and Stoikov, 2006"** (`online-snapshots/hummingbot-as-deep-dive.md:169`) and link the preprint, but the spread formula is the published 2008 one.

## Read depth
- **Read:** both posts in full, the guide's formula images on its page images.
- **Unread:** Hummingbot's code for the strategy.

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [hft-in-a-limit-order-book](hft-in-a-limit-order-book.md).
