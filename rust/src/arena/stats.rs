//! arena/stats.py's statistics whose cost grows with a grid's cells, ported function for function
//! and to the bit: `cscv` (Bailey et al.'s PBO), `mean_correlation` (the DSR's independent
//! trials) and `snooping` (Hansen's SPA and Romano and Wolf's StepM on one stationary bootstrap).
//! The formulas are cited in the Python. What makes them exact: CPython's `math.fsum` (behind
//! `statistics.fmean`), its compensated `sum()` (`py::sum`), `random.Random`'s `sample` and
//! `randrange` (`pyrandom.rs`), and libm's `log` and `pow`, as CPython calls them.

use crate::support::py;
use crate::support::pyrandom::PyRandom;

extern "C" {
    fn log(x: f64) -> f64;
}

fn ln(x: f64) -> f64 {
    unsafe { log(x) }
}

/// CPython's `math.fsum`: Shewchuk's exact partials, then the sum rounded once, half to even
/// across partials (mathmodule.c). Panics on an infinity or NaN, which the grid never sums.
pub fn fsum(xs: impl IntoIterator<Item = f64>) -> f64 {
    let mut p: Vec<f64> = Vec::new();
    for mut x in xs {
        assert!(x.is_finite(), "fsum of a non-finite value");
        let mut i = 0;
        for j in 0..p.len() {
            let mut y = p[j];
            if x.abs() < y.abs() {
                std::mem::swap(&mut x, &mut y);
            }
            let hi = x + y;
            let lo = y - (hi - x);
            if lo != 0.0 {
                p[i] = lo;
                i += 1;
            }
            x = hi;
        }
        p.truncate(i);
        if x != 0.0 {
            assert!(x.is_finite(), "intermediate overflow in fsum");
            p.push(x);
        }
    }
    let mut n = p.len();
    let mut hi = 0.0;
    let mut lo = 0.0;
    if n > 0 {
        n -= 1;
        hi = p[n];
        while n > 0 {
            let x = hi;
            n -= 1;
            let y = p[n];
            hi = x + y;
            let yr = hi - x;
            lo = y - yr;
            if lo != 0.0 {
                break;
            }
        }
        if n > 0 && ((lo < 0.0 && p[n - 1] < 0.0) || (lo > 0.0 && p[n - 1] > 0.0)) {
            let y = lo * 2.0;
            let x = hi + y;
            let yr = x - hi;
            if y == yr {
                hi = x;
            }
        }
    }
    hi
}

/// `statistics.fmean`: fsum over the count.
pub fn fmean(xs: &[f64]) -> f64 {
    fsum(xs.iter().copied()) / xs.len() as f64
}

/// `random.Random.sample(range(n), k)`, draw for draw.
pub fn sample(rng: &mut PyRandom, n: usize, k: usize) -> Vec<usize> {
    assert!(k <= n);
    let mut setsize = 21usize;
    if k > 5 {
        setsize += 4usize.pow((ln((k * 3) as f64) / ln(4.0)).ceil() as u32);
    }
    let mut result = Vec::with_capacity(k);
    if n <= setsize {
        let mut pool: Vec<usize> = (0..n).collect();
        for i in 0..k {
            let j = rng.randbelow((n - i) as u64) as usize;
            result.push(pool[j]);
            pool[j] = pool[n - i - 1];
        }
    } else {
        let mut selected = std::collections::HashSet::new();
        for _ in 0..k {
            let mut j = rng.randbelow(n as u64) as usize;
            while selected.contains(&j) {
                j = rng.randbelow(n as u64) as usize;
            }
            selected.insert(j);
            result.push(j);
        }
    }
    result
}

fn comb(n: usize, k: usize) -> u128 {
    (0..k).fold(1u128, |acc, i| acc * (n - i) as u128 / (i as u128 + 1))
}

/// itertools.combinations(range(n), k), in its (lexicographic) order.
fn combinations(n: usize, k: usize) -> Vec<Vec<usize>> {
    let mut out = Vec::new();
    let mut idx: Vec<usize> = (0..k).collect();
    if k > n {
        return out;
    }
    loop {
        out.push(idx.clone());
        let Some(i) = (0..k).rev().find(|&i| idx[i] != i + n - k) else { return out };
        idx[i] += 1;
        for j in i + 1..k {
            idx[j] = idx[j - 1] + 1;
        }
    }
}

pub struct Cscv {
    pub pbo: f64,
    pub loss: f64,
    pub rank: f64,
    pub splits: usize,
    pub of: u128,
}

/// `cscv`: each halving of the blocks, the best cell on the training half ranked on the other.
pub fn cscv(columns: &[Vec<f64>], max_splits: usize, seed: i64) -> Cscv {
    let (n, s) = (columns.len(), columns[0].len());
    let of = comb(s, s / 2);
    let halvings: Vec<Vec<usize>> = if of <= max_splits as u128 {
        combinations(s, s / 2)
    } else {
        let mut rng = PyRandom::from_int(seed);
        let mut seen = std::collections::BTreeSet::new();
        while seen.len() < max_splits {
            let mut train = sample(&mut rng, s, s / 2);
            train.sort_unstable();
            seen.insert(train);
        }
        seen.into_iter().collect()
    };
    let totals: Vec<f64> = columns.iter().map(|c| py::sum(c.iter().copied())).collect();
    let (mut overfit, mut losses) = (0usize, 0usize);
    let mut ranks = Vec::with_capacity(halvings.len());
    let mut inside = vec![0.0; n];
    let mut outside = vec![0.0; n];
    for train in &halvings {
        for (k, column) in columns.iter().enumerate() {
            inside[k] = py::sum(train.iter().map(|&i| column[i]));
            outside[k] = totals[k] - inside[k];
        }
        let mut best = 0;
        for k in 1..n {
            if inside[k] > inside[best] {
                best = k;
            }
        }
        let mine = outside[best];
        let below = outside.iter().filter(|&&v| v < mine).count();
        let equal = outside.iter().filter(|&&v| v == mine).count();
        let rank = below as f64 + (equal + 1) as f64 / 2.0;
        let w = rank / (n + 1) as f64;
        overfit += (ln(w / (1.0 - w)) <= 0.0) as usize;
        losses += (mine < 0.0) as usize;
        ranks.push(w);
    }
    let count = halvings.len() as f64;
    Cscv { pbo: overfit as f64 / count, loss: losses as f64 / count, rank: fmean(&ranks), splits: halvings.len(), of }
}

/// `mean_correlation`: the mean over every pair of standardized columns of their correlation.
pub fn mean_correlation(scaled: &[Vec<f64>]) -> Option<f64> {
    let m = scaled.len();
    if m < 2 {
        return None;
    }
    let mut values = Vec::with_capacity(m * (m - 1) / 2);
    for i in 0..m {
        let a = &scaled[i];
        for b in &scaled[i + 1..] {
            values.push(py::sum(a.iter().zip(b).map(|(x, y)| x * y)) / a.len() as f64);
        }
    }
    Some(fmean(&values))
}

/// `omega2`: Hansen's variance of sqrt(n) times the mean under the stationary bootstrap.
pub fn omega2(d: &[f64], q: f64) -> f64 {
    let n = d.len();
    let mean = fmean(d);
    let c: Vec<f64> = d.iter().map(|x| x - mean).collect();
    let nf = n as f64;
    let mut total = py::sum(c.iter().map(|x| x * x)) / nf;
    for i in 1..n {
        let kappa = (n - i) as f64 / nf * py::powf(1.0 - q, i as f64) + i as f64 / nf * py::powf(1.0 - q, (n - i) as f64);
        if kappa < 1e-12 {
            continue;
        }
        total += 2.0 * kappa * py::sum(c.iter().zip(&c[i..]).map(|(x, y)| x * y)) / nf;
    }
    total
}

/// `_scales`: each column's sqrt(omega2), floored at 1e-6.
pub fn scales(d: &[Vec<f64>], q: f64) -> Vec<f64> {
    d.iter().map(|c| py::max(omega2(c, q), 1e-12).sqrt()).collect()
}

/// `bootstrap_means`: each resample's mean of every column (Politis and Romano's stationary bootstrap).
pub fn bootstrap_means(d: &[Vec<f64>], q: f64, boot: usize, seed: i64) -> Vec<Vec<f64>> {
    let n = d[0].len();
    let mut rng = PyRandom::from_int(seed);
    let mut idx = vec![0usize; n];
    (0..boot)
        .map(|_| {
            let mut t = rng.randbelow(n as u64) as usize;
            for slot in idx.iter_mut() {
                *slot = t;
                t = if rng.random() < q { rng.randbelow(n as u64) as usize } else { (t + 1) % n };
            }
            d.iter().map(|column| py::sum(idx.iter().map(|&i| column[i])) / n as f64).collect()
        })
        .collect()
}

/// Python's `max` over a non-empty sequence of floats: the first of the largest.
fn first_max(xs: impl Iterator<Item = f64>) -> f64 {
    let mut it = xs;
    let mut best = it.next().expect("max of nothing");
    for x in it {
        if x > best {
            best = x;
        }
    }
    best
}

/// `spa`: Hansen's p-values (l, c, u) that no column of gains has a positive mean.
pub fn spa(d: &[Vec<f64>], omegas: &[f64], draws: &[Vec<f64>]) -> [f64; 3] {
    let n = d[0].len() as f64;
    let root = n.sqrt();
    let means: Vec<f64> = d.iter().map(|c| fmean(c)).collect();
    let t = py::max(0.0, first_max(means.iter().zip(omegas).map(|(m, w)| root * m / w)));
    let loglog = (2.0 * ln(ln(n))).sqrt();
    let shifts = [
        means.iter().map(|&m| py::max(0.0, m)).collect::<Vec<f64>>(),
        means.iter().zip(omegas).map(|(&m, &w)| if m >= -w / root * loglog { m } else { 0.0 }).collect(),
        means.clone(),
    ];
    let mut out = [0.0; 3];
    for (k, shift) in shifts.iter().enumerate() {
        let above = draws
            .iter()
            .filter(|draw| py::max(0.0, first_max(draw.iter().zip(shift).zip(omegas).map(|((x, s), w)| root * (x - s) / w))) > t)
            .count();
        out[k] = above as f64 / draws.len() as f64;
    }
    out
}

/// `stepm`: the columns whose mean gain is significantly positive, the familywise error at alpha.
pub fn stepm(d: &[Vec<f64>], omegas: &[f64], draws: &[Vec<f64>], alpha: f64) -> Vec<usize> {
    let n = d[0].len() as f64;
    let root = n.sqrt();
    let means: Vec<f64> = d.iter().map(|c| fmean(c)).collect();
    let z: Vec<f64> = means.iter().zip(omegas).map(|(m, w)| root * m / w).collect();
    let centred: Vec<Vec<f64>> = draws.iter().map(|draw| draw.iter().zip(&means).zip(omegas).map(|((x, m), w)| root * (x - m) / w).collect()).collect();
    let mut active: Vec<usize> = (0..d.len()).collect();
    let mut rejected = Vec::new();
    while !active.is_empty() {
        let mut maxima: Vec<f64> = centred.iter().map(|draw| first_max(active.iter().map(|&k| draw[k]))).collect();
        maxima.sort_by(|a, b| a.partial_cmp(b).expect("no NaN"));
        let len = maxima.len();
        let c = maxima[(len - 1).min(((1.0 - alpha) * len as f64).ceil() as usize - 1)];
        let newly: Vec<usize> = active.iter().copied().filter(|&k| z[k] > c).collect();
        if newly.is_empty() {
            break;
        }
        active.retain(|k| !newly.contains(k));
        rejected.extend(newly);
    }
    rejected.sort_unstable();
    rejected
}

/// `snooping`: SPA's p-values and StepM's columns on one studentization and one set of resamples.
pub fn snooping(d: &[Vec<f64>], q: f64, boot: usize, alpha: f64, seed: i64) -> ([f64; 3], Vec<usize>) {
    let omegas = scales(d, q);
    let draws = bootstrap_means(d, q, boot, seed);
    (spa(d, &omegas, &draws), stepm(d, &omegas, &draws, alpha))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fsum_as_cpython() {
        // CPython: math.fsum([0.1] * 10) == 1.0; fsum([1e-16, 1, 1e16]) == 1.0000000000000002e16; fsum([1e100, 1.0, -1e100, 1e-100, 1e50, -1.0, -1e50]) == 1e-100
        assert_eq!(fsum(vec![0.1; 10]), 1.0);
        assert_eq!(fsum([1e-16, 1.0, 1e16]), 1.0000000000000002e16);
        assert_eq!(fsum([1e100, 1.0, -1e100, 1e-100, 1e50, -1.0, -1e50]), 1e-100);
        assert_eq!(fsum(Vec::<f64>::new()), 0.0);
    }

    #[test]
    fn sample_and_combinations_as_cpython() {
        // CPython 3.12: r = random.Random(0); [sorted(r.sample(range(18), 9)) for _ in range(2)]
        let mut r = PyRandom::from_int(0);
        let mut a = sample(&mut r, 18, 9);
        let mut b = sample(&mut r, 18, 9);
        a.sort_unstable();
        b.sort_unstable();
        assert_eq!((a, b), (vec![1, 4, 6, 7, 8, 12, 13, 14, 17], vec![1, 2, 4, 6, 9, 11, 12, 14, 15]));
        assert_eq!(combinations(4, 2), [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]]);
        assert_eq!(comb(18, 9), 48620);
    }
}
