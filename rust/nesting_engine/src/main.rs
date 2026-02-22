mod geometry;
mod io;

use std::io::{self as stdio, BufReader, BufWriter, Write};

use crate::{geometry::pipeline::run_inflate_pipeline, io::pipeline_io::PipelineRequest};

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|a| a == "--version") {
        println!("nesting_engine {}", env!("CARGO_PKG_VERSION"));
        return;
    }

    if args.iter().any(|a| a == "--help") {
        println!("Usage: nesting_engine [--version] [--help] [inflate-parts]");
        println!("NFP-based nesting engine (scaffold)");
        return;
    }

    if args.len() >= 2 && args[1] == "inflate-parts" {
        if let Err(err) = run_inflate_parts() {
            eprintln!("nesting_engine inflate-parts: {err}");
            std::process::exit(1);
        }
        return;
    }

    eprintln!("nesting_engine: no input");
    std::process::exit(1);
}

fn run_inflate_parts() -> Result<(), String> {
    let stdin = stdio::stdin();
    let reader = BufReader::new(stdin.lock());
    let req: PipelineRequest = serde_json::from_reader(reader)
        .map_err(|err| format!("invalid PipelineRequest JSON on stdin: {err}"))?;

    let resp = run_inflate_pipeline(req);

    let stdout = stdio::stdout();
    let mut writer = BufWriter::new(stdout.lock());
    serde_json::to_writer(&mut writer, &resp)
        .map_err(|err| format!("failed to write PipelineResponse JSON: {err}"))?;
    writer
        .write_all(b"\n")
        .map_err(|err| format!("failed to finalize output: {err}"))?;
    writer
        .flush()
        .map_err(|err| format!("failed to flush output: {err}"))?;
    Ok(())
}
