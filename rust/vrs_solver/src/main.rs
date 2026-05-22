mod adapter;
mod geometry;
mod io;
mod item;
mod optimizer;
mod sheet;

use std::collections::HashMap;
use std::fs;

fn parse_args() -> Result<HashMap<String, String>, String> {
    let mut args = std::env::args().skip(1);
    let mut out = HashMap::new();
    while let Some(k) = args.next() {
        if !k.starts_with("--") {
            return Err(format!("unexpected argument: {k}"));
        }
        let v = args
            .next()
            .ok_or_else(|| format!("missing value for argument: {k}"))?;
        out.insert(k, v);
    }
    Ok(out)
}

fn main() -> Result<(), String> {
    let args = parse_args()?;
    let input_path = args
        .get("--input")
        .ok_or_else(|| "--input is required".to_string())?;
    let output_path = args
        .get("--output")
        .ok_or_else(|| "--output is required".to_string())?;

    let content = fs::read_to_string(input_path)
        .map_err(|e| format!("failed to read input json {input_path}: {e}"))?;
    let input: io::SolverInput =
        serde_json::from_str(&content).map_err(|e| format!("invalid input json: {e}"))?;

    if input.contract_version != "v1" {
        return Err("unsupported contract_version; expected v1".to_string());
    }

    let output = adapter::solve(input)?;
    let output_json = serde_json::to_string_pretty(&output)
        .map_err(|e| format!("failed to serialize output json: {e}"))?;
    fs::write(output_path, format!("{output_json}\n"))
        .map_err(|e| format!("failed to write output json {output_path}: {e}"))?;

    Ok(())
}
