use std::io::{self, BufRead};

fn main() {
    for line in io::stdin().lock().lines() {
        let Ok(line) = line else {
            std::process::exit(70)
        };
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() != 3 || parts[0] != "V1" {
            println!("ERR protocol");
            continue;
        }
        let Ok(value) = parts[2].parse::<u32>() else {
            println!("ERR value");
            continue;
        };
        if value > 100000 {
            println!("ERR range");
            continue;
        }
        println!("OK {} {}", parts[1], value);
    }
}
