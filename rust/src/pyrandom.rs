//! Python's `random.Random` (CPython 3.12), draw for draw: the engine seeds two of them (fill-ratio
//! liquidity and the arrival shuffle), so a seeded Rust run matches a seeded Python run.
//!
//! MT19937 and its seeding are CPython's `_randommodule.c`; `random`, `shuffle`, `_randbelow` and
//! `binomialvariate` are `Lib/random.py`. One approximation: `binomialvariate`'s rejection test
//! calls the C library's `lgamma`, where CPython has its own; they differ by a few ulps, which can
//! only flip a draw whose test lands within that of the bound.

const N: usize = 624;
const M: usize = 397;

extern "C" {
    fn lgamma(x: f64) -> f64;
}

#[derive(Clone)]
pub struct PyRandom {
    mt: [u32; N],
    index: usize,
}

impl PyRandom {
    fn init_genrand(seed: u32) -> Self {
        let mut mt = [0u32; N];
        mt[0] = seed;
        for i in 1..N {
            mt[i] = 1812433253u32.wrapping_mul(mt[i - 1] ^ (mt[i - 1] >> 30)).wrapping_add(i as u32);
        }
        PyRandom { mt, index: N }
    }

    fn init_by_array(key: &[u32]) -> Self {
        let mut r = Self::init_genrand(19650218);
        let mt = &mut r.mt;
        let (mut i, mut j) = (1usize, 0usize);
        for _ in 0..N.max(key.len()) {
            mt[i] = (mt[i] ^ (mt[i - 1] ^ (mt[i - 1] >> 30)).wrapping_mul(1664525)).wrapping_add(key[j]).wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                mt[0] = mt[N - 1];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
        }
        for _ in 0..N - 1 {
            mt[i] = (mt[i] ^ (mt[i - 1] ^ (mt[i - 1] >> 30)).wrapping_mul(1566083941)).wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                mt[0] = mt[N - 1];
                i = 1;
            }
        }
        mt[0] = 0x8000_0000;
        r
    }

    /// From a non-negative integer given as little-endian bytes (CPython's `random_seed`).
    fn from_le_bytes(bytes: &[u8]) -> Self {
        let used = bytes.iter().rposition(|&b| b != 0).map_or(0, |k| k + 1);
        let words = used.div_ceil(4).max(1);
        let key: Vec<u32> = (0..words)
            .map(|w| (0..4).fold(0u32, |acc, b| acc | (*bytes.get(w * 4 + b).unwrap_or(&0) as u32) << (8 * b)))
            .collect();
        Self::init_by_array(&key)
    }

    /// random.Random(seed) for an int seed (its absolute value is used, as in CPython).
    pub fn from_int(seed: i64) -> Self {
        Self::from_le_bytes(&seed.unsigned_abs().to_le_bytes())
    }

    /// random.Random(text): the seed is int.from_bytes(text + sha512(text)), big-endian.
    pub fn from_str(text: &str) -> Self {
        let mut bytes = text.as_bytes().to_vec();
        bytes.extend_from_slice(&crate::sha512::digest(text.as_bytes()));
        bytes.reverse();
        Self::from_le_bytes(&bytes)
    }

    pub fn next_u32(&mut self) -> u32 {
        if self.index >= N {
            for k in 0..N {
                let y = (self.mt[k] & 0x8000_0000) | (self.mt[(k + 1) % N] & 0x7fff_ffff);
                self.mt[k] = self.mt[(k + M) % N] ^ (y >> 1) ^ if y & 1 == 1 { 0x9908_b0df } else { 0 };
            }
            self.index = 0;
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c_5680;
        y ^= (y << 15) & 0xefc6_0000;
        y ^ (y >> 18)
    }

    /// random.random(): 53 bits from two draws.
    pub fn random(&mut self) -> f64 {
        let a = (self.next_u32() >> 5) as f64;
        let b = (self.next_u32() >> 6) as f64;
        (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)
    }

    /// getrandbits(k), 1 <= k <= 32.
    pub fn getrandbits(&mut self, k: u32) -> u32 {
        self.next_u32() >> (32 - k)
    }

    /// _randbelow_with_getrandbits(n), 0 < n < 2**32.
    pub fn randbelow(&mut self, n: u64) -> u64 {
        let k = 64 - n.leading_zeros();
        loop {
            let r = self.getrandbits(k) as u64;
            if r < n {
                return r;
            }
        }
    }

    pub fn shuffle<T>(&mut self, x: &mut [T]) {
        for i in (1..x.len()).rev() {
            let j = self.randbelow(i as u64 + 1) as usize;
            x.swap(i, j);
        }
    }

    pub fn binomialvariate(&mut self, n: i64, p: f64) -> i64 {
        assert!(n >= 0 && (0.0..=1.0).contains(&p));
        if p == 0.0 {
            return 0;
        }
        if p == 1.0 {
            return n;
        }
        if n == 1 {
            return (self.random() < p) as i64;
        }
        if p > 0.5 {
            return n - self.binomialvariate(n, 1.0 - p);
        }
        if (n as f64) * p < 10.0 {
            let (mut x, mut y) = (0i64, 0i64);
            let c = (1.0 - p).log2();
            if c == 0.0 {
                return x;
            }
            loop {
                y += (self.random().log2() / c).floor() as i64 + 1;
                if y > n {
                    return x;
                }
                x += 1;
            }
        }
        let nf = n as f64;
        let spq = (nf * p * (1.0 - p)).sqrt();
        let b = 1.15 + 2.53 * spq;
        let a = -0.0873 + 0.0248 * b + 0.01 * p;
        let c = nf * p + 0.5;
        let vr = 0.92 - 4.2 / b;
        let mut setup: Option<(f64, f64, f64, f64)> = None; // alpha, lpq, m, h
        loop {
            let u = self.random() - 0.5;
            let us = 0.5 - u.abs();
            let k = ((2.0 * a / us + b) * u + c).floor();
            if k < 0.0 || k > nf {
                continue;
            }
            let mut v = self.random();
            if us >= 0.07 && v <= vr {
                return k as i64;
            }
            let (alpha, lpq, m, h) = *setup.get_or_insert_with(|| {
                let m = ((nf + 1.0) * p).floor();
                let h = unsafe { lgamma(m + 1.0) + lgamma(nf - m + 1.0) };
                ((2.83 + 5.1 / b) * spq, (p / (1.0 - p)).ln(), m, h)
            });
            v *= alpha / (a / (us * us) + b);
            if v.ln() <= h - unsafe { lgamma(k + 1.0) + lgamma(nf - k + 1.0) } + (k - m) * lpq {
                return k as i64;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::PyRandom;

    // The expected values were printed by CPython 3.12.15.
    #[test]
    fn int_seeds() {
        let mut r = PyRandom::from_int(0);
        assert_eq!([r.random(), r.random(), r.random()], [0.8444218515250481, 0.7579544029403025, 0.420571580830845]);
        assert_eq!(r.getrandbits(5), 8);
        assert_eq!(PyRandom::from_int(123456789123).random(), 0.6881271306912081);
    }

    #[test]
    fn string_seed_and_shuffle() {
        let mut r = PyRandom::from_str("arrival-0");
        let mut x = [0, 1, 2, 3, 4];
        r.shuffle(&mut x);
        assert_eq!(x, [1, 3, 0, 2, 4]);
        assert_eq!(r.random(), 0.4657907145295789);
    }

    #[test]
    fn binomial() {
        let mut r = PyRandom::from_int(7);
        let cases = [(25, 0.5), (5, 0.3), (1, 0.3), (30, 0.8), (0, 0.5), (40, 0.6), (200, 0.5), (3, 0.9)];
        let found: Vec<i64> = cases.iter().map(|&(n, p)| r.binomialvariate(n, p)).collect();
        assert_eq!(found, [11, 1, 0, 27, 0, 30, 98, 3]);
        assert_eq!(r.random(), 0.22323896460701453);
    }
}
