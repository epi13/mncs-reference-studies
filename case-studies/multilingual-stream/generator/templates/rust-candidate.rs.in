use std::env;
use std::io::{self, Read};
use std::process::ExitCode;

const MAX_INPUT: usize = 1_048_576;
const MAX_VALUE: u32 = 100_000;
const PRIME: u32 = 16_777_619;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ParseError {
    Invalid,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Stats {
    count: u64,
    sum: u64,
    checksum: u32,
}

impl Stats {
    fn push(&mut self, value: u32) -> Result<(), ParseError> {
        self.count = self.count.checked_add(1).ok_or(ParseError::Invalid)?;
        self.sum = self
            .sum
            .checked_add(u64::from(value))
            .ok_or(ParseError::Invalid)?;
        self.checksum = self.checksum.wrapping_mul(PRIME) ^ value;
        Ok(())
    }
}

fn empty_stats() -> Stats {
    Stats {
        count: 0,
        sum: 0,
        checksum: 0,
    }
}

fn parse_decimal(record: &[u8]) -> Result<u32, ParseError> {
    if record.is_empty() {
        return Err(ParseError::Invalid);
    }

    let mut value = 0_u32;
    for &byte in record {
        if !byte.is_ascii_digit() {
            return Err(ParseError::Invalid);
        }
        value = value.checked_mul(10).ok_or(ParseError::Invalid)?;
        value = value
            .checked_add(u32::from(byte - b'0'))
            .ok_or(ParseError::Invalid)?;
        if value > MAX_VALUE {
            return Err(ParseError::Invalid);
        }
    }
    Ok(value)
}

fn reference(input: &[u8]) -> Result<Stats, ParseError> {
    if input.len() > MAX_INPUT || input.contains(&0) {
        return Err(ParseError::Invalid);
    }

    let mut stats = empty_stats();
    if input.is_empty() {
        return Ok(stats);
    }

    let mut start = 0;
    for (index, &byte) in input.iter().enumerate() {
        if byte == b'\n' {
            let mut end = index;
            if end > start && input[end - 1] == b'\r' {
                end -= 1;
            }
            stats.push(parse_decimal(&input[start..end])?)?;
            start = index + 1;
        }
    }
    if start < input.len() {
        stats.push(parse_decimal(&input[start..])?)?;
    }
    Ok(stats)
}

fn candidate(input: &[u8]) -> Result<Stats, ParseError> {
    if input.len() > MAX_INPUT || input.contains(&0) {
        return Err(ParseError::Invalid);
    }

    let mut stats = empty_stats();
    let mut value = 0_u32;
    let mut digits = 0_u8;
    let mut index = 0_usize;
    while index < input.len() {
        let byte = input[index];
        if byte.is_ascii_digit() {
            digits = digits.checked_add(1).ok_or(ParseError::Invalid)?;
            value = value.checked_mul(10).ok_or(ParseError::Invalid)?;
            value = value
                .checked_add(u32::from(byte - b'0'))
                .ok_or(ParseError::Invalid)?;
            if value > MAX_VALUE {
                return Err(ParseError::Invalid);
            }
            index += 1;
            continue;
        }

        if byte == b'\r' && index + 1 < input.len() && input[index + 1] == b'\n' {
            if digits == 0 {
                return Err(ParseError::Invalid);
            }
            stats.push(value)?;
            value = 0;
            digits = 0;
            index += 2;
            continue;
        }
        if byte == b'\n' {
            if digits == 0 {
                return Err(ParseError::Invalid);
            }
            stats.push(value)?;
            value = 0;
            digits = 0;
            index += 1;
            continue;
        }
        return Err(ParseError::Invalid);
    }

    if digits != 0 {
        stats.push(value)?;
    }
    Ok(stats)
}

fn execute(mode: &str, input: &[u8]) -> Result<Stats, ParseError> {
    match mode {
        "reference" => reference(input),
        "candidate" => candidate(input),
        _ => Err(ParseError::Invalid),
    }
}

fn main() -> ExitCode {
    let Some(mode) = env::args().nth(1) else {
        eprintln!("invalid invocation");
        return ExitCode::from(64);
    };
    if mode != "reference" && mode != "candidate" {
        eprintln!("invalid invocation");
        return ExitCode::from(64);
    }

    let mut input = Vec::new();
    let read_result = io::stdin()
        .take((MAX_INPUT + 1) as u64)
        .read_to_end(&mut input);
    if read_result.is_err() || input.len() > MAX_INPUT {
        eprintln!("invalid input");
        return ExitCode::from(2);
    }

    match execute(&mode, &input) {
        Ok(stats) => {
            println!(
                "{{\"count\":{},\"sum\":{},\"checksum\":{}}}",
                stats.count, stats.sum, stats.checksum
            );
            ExitCode::SUCCESS
        }
        Err(ParseError::Invalid) => {
            eprintln!("invalid input");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn implementations_agree() {
        let corpus = b"0\n1\n42\r\n100000";
        assert_eq!(reference(corpus), candidate(corpus));
    }

    #[test]
    fn malformed_is_rejected() {
        let cases: [&[u8]; 5] = [b"\n", b"-1\n", b"1 2\n", b"100001\n", b"1\r2\n"];
        for case in cases {
            assert!(reference(case).is_err());
            assert!(candidate(case).is_err());
        }
    }
}
