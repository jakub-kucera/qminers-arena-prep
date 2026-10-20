//! Just enough JSON for the bots' settings and the batch command: what Python's `json.dumps`
//! writes (Infinity and NaN included). Integers and floats stay apart, as they do in Python, so a
//! bot can refuse a float where its Python twin would only work with an int.

use std::fmt::Write as _;

#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    Object(Vec<(String, Value)>), // in the file's order, as a Python dict keeps it
}

impl Value {
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Object(items) => items.iter().find(|(k, _)| k == key).map(|(_, v)| v),
            _ => None,
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Value::Null)
    }

    /// A number (ints included) as a float, as Python's arithmetic would mix them.
    pub fn as_f64(&self) -> Option<f64> {
        match *self {
            Value::Int(v) => Some(v as f64),
            Value::Float(v) => Some(v),
            Value::Bool(v) => Some(v as i64 as f64),
            _ => None,
        }
    }

    pub fn as_i64(&self) -> Option<i64> {
        match *self {
            Value::Int(v) => Some(v),
            Value::Bool(v) => Some(v as i64),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s),
            _ => None,
        }
    }

    pub fn as_object(&self) -> Option<&[(String, Value)]> {
        match self {
            Value::Object(items) => Some(items),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&[Value]> {
        match self {
            Value::List(items) => Some(items),
            _ => None,
        }
    }

    /// Python's truth value.
    pub fn truthy(&self) -> bool {
        match self {
            Value::Null => false,
            Value::Bool(v) => *v,
            Value::Int(v) => *v != 0,
            Value::Float(v) => *v != 0.0,
            Value::Str(s) => !s.is_empty(),
            Value::List(v) => !v.is_empty(),
            Value::Object(v) => !v.is_empty(),
        }
    }
}

pub fn parse(text: &str) -> Result<Value, String> {
    let mut p = Parser { s: text.as_bytes(), k: 0 };
    let value = p.value()?;
    p.space();
    if p.k != p.s.len() {
        return Err(format!("trailing characters at {}", p.k));
    }
    Ok(value)
}

struct Parser<'a> {
    s: &'a [u8],
    k: usize,
}

impl Parser<'_> {
    fn space(&mut self) {
        while self.k < self.s.len() && self.s[self.k].is_ascii_whitespace() {
            self.k += 1;
        }
    }

    fn eat(&mut self, word: &str) -> bool {
        if self.s[self.k..].starts_with(word.as_bytes()) {
            self.k += word.len();
            true
        } else {
            false
        }
    }

    fn value(&mut self) -> Result<Value, String> {
        self.space();
        let Some(&c) = self.s.get(self.k) else { return Err("unexpected end".into()) };
        match c {
            b'{' => {
                self.k += 1;
                let mut items = Vec::new();
                self.space();
                if self.eat("}") {
                    return Ok(Value::Object(items));
                }
                loop {
                    self.space();
                    let Value::Str(key) = self.value()? else { return Err(format!("expected a key at {}", self.k)) };
                    self.space();
                    if !self.eat(":") {
                        return Err(format!("expected : at {}", self.k));
                    }
                    items.push((key, self.value()?));
                    self.space();
                    if self.eat("}") {
                        return Ok(Value::Object(items));
                    }
                    if !self.eat(",") {
                        return Err(format!("expected , or }} at {}", self.k));
                    }
                }
            }
            b'[' => {
                self.k += 1;
                let mut items = Vec::new();
                self.space();
                if self.eat("]") {
                    return Ok(Value::List(items));
                }
                loop {
                    items.push(self.value()?);
                    self.space();
                    if self.eat("]") {
                        return Ok(Value::List(items));
                    }
                    if !self.eat(",") {
                        return Err(format!("expected , or ] at {}", self.k));
                    }
                }
            }
            b'"' => self.string().map(Value::Str),
            _ if self.eat("null") => Ok(Value::Null),
            _ if self.eat("true") => Ok(Value::Bool(true)),
            _ if self.eat("false") => Ok(Value::Bool(false)),
            _ if self.eat("NaN") => Ok(Value::Float(f64::NAN)),
            _ if self.eat("Infinity") => Ok(Value::Float(f64::INFINITY)),
            _ if self.eat("-Infinity") => Ok(Value::Float(f64::NEG_INFINITY)),
            _ => self.number(),
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.k += 1;
        let mut out = String::new();
        loop {
            let Some(&c) = self.s.get(self.k) else { return Err("unterminated string".into()) };
            self.k += 1;
            match c {
                b'"' => return Ok(out),
                b'\\' => {
                    let e = *self.s.get(self.k).ok_or("bad escape")?;
                    self.k += 1;
                    match e {
                        b'n' => out.push('\n'),
                        b't' => out.push('\t'),
                        b'r' => out.push('\r'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'u' => {
                            let hex = std::str::from_utf8(self.s.get(self.k..self.k + 4).ok_or("bad \\u")?).map_err(|_| "bad \\u")?;
                            let mut code = u32::from_str_radix(hex, 16).map_err(|_| "bad \\u")?;
                            self.k += 4;
                            if (0xD800..0xDC00).contains(&code) && self.s[self.k..].starts_with(b"\\u") {
                                let low = std::str::from_utf8(&self.s[self.k + 2..self.k + 6]).map_err(|_| "bad \\u")?;
                                let low = u32::from_str_radix(low, 16).map_err(|_| "bad \\u")?;
                                code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00);
                                self.k += 6;
                            }
                            out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                        }
                        other => out.push(other as char),
                    }
                }
                _ => {
                    // copy a run of plain UTF-8 bytes
                    let start = self.k - 1;
                    while self.k < self.s.len() && self.s[self.k] != b'"' && self.s[self.k] != b'\\' {
                        self.k += 1;
                    }
                    out.push_str(std::str::from_utf8(&self.s[start..self.k]).map_err(|_| "bad UTF-8")?);
                }
            }
        }
    }

    fn number(&mut self) -> Result<Value, String> {
        let start = self.k;
        while self.k < self.s.len() && matches!(self.s[self.k], b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9') {
            self.k += 1;
        }
        let text = std::str::from_utf8(&self.s[start..self.k]).unwrap();
        if text.is_empty() {
            return Err(format!("unexpected character at {start}"));
        }
        if text.contains(['.', 'e', 'E']) {
            text.parse().map(Value::Float).map_err(|_| format!("bad number {text}"))
        } else {
            text.parse().map(Value::Int).map_err(|_| format!("bad integer {text} (too large?)"))
        }
    }
}

/// A float as Python's json module writes it, read back exactly by `json.loads`.
pub fn float(out: &mut String, v: f64) {
    if v.is_nan() {
        out.push_str("NaN");
    } else if v.is_infinite() {
        out.push_str(if v > 0.0 { "Infinity" } else { "-Infinity" });
    } else {
        let _ = write!(out, "{v:?}");
    }
}

pub fn string(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_what_python_writes() {
        let v = parse(r#"{"a": [1, 2.5, -3e2, null, true], "b": {"c": "x\"yé"}, "d": Infinity, "e": -Infinity}"#).unwrap();
        assert_eq!(v.get("a").unwrap().as_list().unwrap()[0], Value::Int(1));
        assert_eq!(v.get("a").unwrap().as_list().unwrap()[2], Value::Float(-300.0));
        assert_eq!(v.get("b").unwrap().get("c").unwrap().as_str(), Some("x\"yé"));
        assert_eq!(v.get("d").unwrap().as_f64(), Some(f64::INFINITY));
        assert_eq!(v.get("e").unwrap().as_f64(), Some(f64::NEG_INFINITY));
        let mut out = String::new();
        float(&mut out, 0.1 + 0.2);
        assert_eq!(out, "0.30000000000000004");
    }
}
