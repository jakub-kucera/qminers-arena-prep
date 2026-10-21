//! Python's arithmetic where it isn't IEEE's plain operations, for the zoo's twins and arena.sim:
//! CPython 3.12's `sum()` of floats (Neumaier's compensated sum) and of ints and floats mixed,
//! `round(x, n)`, floor division, `max`/`min` on floats (the first of equals), and numpy's pairwise
//! `mean` and `std`.

/// CPython 3.12's `sum(xs)` of floats, start 0: the first item as is, the rest compensated.
pub fn sum(xs: impl IntoIterator<Item = f64>) -> f64 {
    let mut it = xs.into_iter();
    let Some(first) = it.next() else { return 0.0 };
    let mut f = 0.0 + first; // the start, int 0, plus the first item
    let mut c = 0.0f64;
    for x in it {
        let t = f + x;
        if f.abs() >= x.abs() {
            c += (f - t) + x;
        } else {
            c += (x - t) + f;
        }
        f = t;
    }
    if c != 0.0 && c.is_finite() {
        f += c;
    }
    f
}

/// A Python number that is an int or a float (arena.sim's mids: a one-sided book's is its price, an int).
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Num {
    Int(i64),
    Float(f64),
}

impl Num {
    pub fn f64(self) -> f64 {
        match self {
            Num::Int(v) => v as f64,
            Num::Float(v) => v,
        }
    }

    /// Python's `self / n`, a true division by an int (exact ints divide correctly rounded, as f64 does).
    pub fn div(self, n: i64) -> f64 {
        self.f64() / n as f64
    }
}

/// CPython 3.12's `sum(xs)` of ints and floats, start 0: the ints exactly until the first float,
/// then that sum as a float plus the float, the floats after it compensated (Neumaier) and the
/// ints after it added plainly.
pub fn sum_num(xs: &[Num]) -> Num {
    let mut i = 0i64;
    let mut k = 0;
    while k < xs.len() {
        match xs[k] {
            Num::Int(v) => i += v,
            Num::Float(_) => break,
        }
        k += 1;
    }
    if k == xs.len() {
        return Num::Int(i);
    }
    let mut f = i as f64 + xs[k].f64();
    let mut c = 0.0f64;
    for &x in &xs[k + 1..] {
        match x {
            Num::Float(x) => {
                let t = f + x;
                if f.abs() >= x.abs() {
                    c += (f - t) + x;
                } else {
                    c += (x - t) + f;
                }
                f = t;
            }
            Num::Int(v) => f += v as f64,
        }
    }
    if c != 0.0 && c.is_finite() {
        f += c;
    }
    Num::Float(f)
}

extern "C" {
    fn pow(x: f64, y: f64) -> f64;
}

/// Python's `x ** 2` on a float: libm's pow (on macOS not always x * x), kept from being folded.
pub fn sq(x: f64) -> f64 {
    unsafe { pow(x, std::hint::black_box(2.0)) }
}

/// Python's `x ** y` on floats.
pub fn powf(x: f64, y: f64) -> f64 {
    unsafe { pow(x, std::hint::black_box(y)) }
}

/// `sum(xs)` where the items are Python ints: exact.
pub fn sum_int(xs: impl IntoIterator<Item = i64>) -> i64 {
    xs.into_iter().sum()
}

/// Python's `round(x, ndigits)` on a float: the correctly rounded decimal, read back.
pub fn round_to(x: f64, ndigits: usize) -> f64 {
    if !x.is_finite() {
        return x;
    }
    format!("{x:.ndigits$}").parse().unwrap()
}

/// Python's `round(x)` on a float: an int, ties to even.
pub fn round(x: f64) -> i64 {
    x.round_ties_even() as i64
}

/// Python's `a // b` on ints.
pub fn floordiv(a: i64, b: i64) -> i64 {
    let q = a / b;
    if (a % b != 0) && ((a < 0) != (b < 0)) {
        q - 1
    } else {
        q
    }
}

/// Python's `max(a, b)`: a unless b is larger.
pub fn max(a: f64, b: f64) -> f64 {
    if b > a {
        b
    } else {
        a
    }
}

/// Python's `min(a, b)`: a unless b is smaller.
pub fn min(a: f64, b: f64) -> f64 {
    if b < a {
        b
    } else {
        a
    }
}

/// numpy's `np.sum` of float64: its identity 0.0 plus the pairwise sum (`pairwise_sum` in loops_utils.h).
pub fn np_sum(a: &[f64]) -> f64 {
    0.0 + pairwise(a)
}

fn pairwise(a: &[f64]) -> f64 {
    const PW_BLOCKSIZE: usize = 128;
    let n = a.len();
    if n < 8 {
        let mut res = 0.0;
        for &x in a {
            res += x;
        }
        res
    } else if n <= PW_BLOCKSIZE {
        let mut r = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]];
        let mut i = 8;
        while i < n - (n % 8) {
            for k in 0..8 {
                r[k] += a[i + k];
            }
            i += 8;
        }
        let mut res = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]));
        while i < n {
            res += a[i];
            i += 1;
        }
        res
    } else {
        let mut n2 = n / 2;
        n2 -= n2 % 8;
        pairwise(&a[..n2]) + pairwise(&a[n2..])
    }
}

/// `np.mean(a)` of float64 (or of ints, cast first).
pub fn np_mean(a: &[f64]) -> f64 {
    np_sum(a) / a.len() as f64
}

/// `np.std(a)` (ddof 0): the root of the mean squared deviation, each step as numpy does it.
pub fn np_std(a: &[f64]) -> f64 {
    let mean = np_mean(a);
    let squares: Vec<f64> = a.iter().map(|&x| (x - mean) * (x - mean)).collect();
    (np_sum(&squares) / a.len() as f64).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compensated_sum_as_cpython() {
        // CPython 3.12: sum([0.1] * 10) == 1.0, a plain loop gives 0.9999999999999999
        assert_eq!(sum(vec![0.1; 10]), 1.0);
        assert_eq!(sum([1e100, 1.0, -1e100, 1.0]), 2.0);
        assert_eq!(sum(Vec::<f64>::new()), 0.0);
    }

    #[test]
    fn mixed_sum_as_cpython() {
        // CPython 3.12: sum([3, 4]) == 7; sum([1, 0.1, 2, 1e16, 1.0, -1e16]) == 4.1; sum([0.1, 1e16, 3, -1e16]) == 4.1
        use Num::{Float, Int};
        assert_eq!(sum_num(&[Int(3), Int(4)]), Int(7));
        assert_eq!(sum_num(&[]), Int(0));
        assert_eq!(sum_num(&[Int(1), Float(0.1), Int(2), Float(1e16), Float(1.0), Float(-1e16)]), Float(4.1));
        assert_eq!(sum_num(&[Float(0.1), Float(1e16), Int(3), Float(-1e16)]), Float(4.1));
    }

    #[test]
    fn rounding_as_python() {
        // Python: round(0.125, 2) == 0.12, round(2.675, 2) == 2.67, round(0.5) == 0, round(1.5) == 2
        assert_eq!(round_to(0.125, 2), 0.12);
        assert_eq!(round_to(0.375, 2), 0.38);
        assert_eq!(round_to(2.675, 2), 2.67);
        assert_eq!(round_to(-1.25, 1), -1.2);
        assert_eq!((round(0.5), round(1.5), round(-2.5)), (0, 2, -2));
        assert_eq!((floordiv(-7, 2), floordiv(7, -2), floordiv(7, 2)), (-4, -4, 3));
        // CPython's round(x, n) on exact ties (odd / 2^(n+1), half to even) and on random values
        for (x, n, expected) in [
            (452518.25, 1, 452518.2), (48017.25, 1, 48017.2), (189298.75, 1, 189298.8), (-385860.75, 1, -385860.8), (131902.75, 1, 131902.8),
            (318139.25, 1, 318139.2), (152359.375, 2, 152359.38), (-112897.625, 2, -112897.62), (-210677.375, 2, -210677.38),
            (-142652.875, 2, -142652.88), (-131614.125, 2, -131614.12), (236246.375, 2, 236246.38), (114168.1875, 3, 114168.188),
            (-47712.1875, 3, -47712.188), (-122139.0625, 3, -122139.062), (-118980.6875, 3, -118980.688), (55523.6875, 3, 55523.688),
            (73467.3125, 3, 73467.312), (7737.328125, 5, 7737.32812), (781.828125, 5, 781.82812), (10654.328125, 5, 10654.32812),
            (-4479.328125, 5, -4479.32812), (16834.171875, 5, 16834.17188), (-29280.578125, 5, -29280.57812), (1780.5595285298368, 5, 1780.55953),
            (152.19430207879714, 2, 152.19), (1738.4858247705797, 2, 1738.49), (-828.6817082326161, 2, -828.68), (-2032.8920801758868, 2, -2032.89),
            (1290.9053894247209, 2, 1290.91), (929.465868935989, 1, 929.5), (-59.916468898852145, 2, -59.92), (5.046375783929307, 2, 5.05),
            (970.1136000238766, 2, 970.11), (2398.2035325397546, 2, 2398.2), (-895.3511610162973, 5, -895.35116), (2521.982635151573, 5, 2521.98264),
            (-260.693304839348, 5, -260.6933), (-1669.1339340539348, 2, -1669.13), (1888.1019517587847, 1, 1888.1),
        ] {
            assert_eq!(round_to(x, n), expected, "round({x}, {n})");
        }
    }
}
