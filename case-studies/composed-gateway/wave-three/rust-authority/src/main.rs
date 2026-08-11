use std::env;
use std::io::{self, BufRead, Write};
use std::thread;
use std::time::Duration;

const AUTHORITY_ID: &str = "rust-authority-v2";
const MAX_VALUE: u32 = 100_000;

fn parse_usize(name: &str) -> Option<usize> {
    env::var(name).ok().and_then(|value| value.parse().ok())
}

fn emit(stdout: &mut impl Write, message: &str) {
    if writeln!(stdout, "{message}").is_err() || stdout.flush().is_err() {
        std::process::exit(73);
    }
}

fn main() {
    let stdout = io::stdout();
    let mut output = stdout.lock();
    emit(&mut output, &format!("READY V2 {AUTHORITY_ID}"));

    let crash_after = parse_usize("MNCS_AUTHORITY_CRASH_AFTER");
    let partial_at = parse_usize("MNCS_AUTHORITY_PARTIAL_AT");
    let delay_ms = parse_usize("MNCS_AUTHORITY_DELAY_MS").unwrap_or(0);
    let wrong_version = env::var("MNCS_AUTHORITY_WRONG_VERSION").ok().as_deref() == Some("1");

    for (index, line) in io::stdin().lock().lines().enumerate() {
        if crash_after == Some(index) {
            std::process::exit(71);
        }
        let Ok(line) = line else {
            std::process::exit(70)
        };
        let parts: Vec<&str> = line.split_whitespace().collect();
        let expected = if wrong_version { "V9" } else { "V2" };
        if parts.len() != 3 || parts[0] != expected {
            emit(&mut output, "ERR protocol");
            continue;
        }
        let Ok(value) = parts[2].parse::<u32>() else {
            emit(&mut output, "ERR value");
            continue;
        };
        if value > MAX_VALUE {
            emit(&mut output, "ERR range");
            continue;
        }
        if delay_ms > 0 {
            thread::sleep(Duration::from_millis(delay_ms as u64));
        }
        if partial_at == Some(index) {
            let _ = write!(output, "OK {}", parts[1]);
            let _ = output.flush();
            std::process::exit(72);
        }
        emit(&mut output, &format!("OK {} {}", parts[1], value));
    }
}
