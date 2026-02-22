mod geometry;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|a| a == "--version") {
        println!("nesting_engine {}", env!("CARGO_PKG_VERSION"));
        return;
    }

    if args.iter().any(|a| a == "--help") {
        println!("Usage: nesting_engine [--version] [--help]");
        println!("NFP-based nesting engine (scaffold)");
        return;
    }

    eprintln!("nesting_engine: no input");
    std::process::exit(1);
}
