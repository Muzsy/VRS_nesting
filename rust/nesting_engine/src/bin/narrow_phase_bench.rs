//! T06m — Narrow-phase strategy correctness equivalence and microbenchmark
//!
//! Runs targeted polygon pair tests comparing own vs i_overlay strategy.
//!
//! Usage:
//!   cargo run --bin narrow_phase_bench --release -- \
//!     --mode equivalence   # correctness tests
//!     --mode microbench    # timing benchmark
//!     --strategy own       # own | i_overlay | both
//!     --pairs 1000         # number of random pairs for microbench

use std::time::Instant;

use nesting_engine::feasibility::{
    can_place, own_polygons_intersect_or_touch,
    i_overlay_narrow,
    aabb::aabb_from_polygon64,
    CanPlaceProfile, PlacedIndex, PlacedPart,
};
use nesting_engine::geometry::scale::mm_to_i64;
use nesting_engine::geometry::types::{Point64, Polygon64};

fn rect(x0: f64, y0: f64, w: f64, h: f64) -> Polygon64 {
    let p = |x: f64, y: f64| Point64 {
        x: mm_to_i64(x),
        y: mm_to_i64(y),
    };
    Polygon64 {
        outer: vec![p(x0, y0), p(x0 + w, y0), p(x0 + w, y0 + h), p(x0, y0 + h)],
        holes: Vec::new(),
    }
}

fn concave_notch() -> Polygon64 {
    // L-shape: 0,0 -> 20,0 -> 20,10 -> 10,10 -> 10,20 -> 0,20 -> close
    let p = |x: f64, y: f64| Point64 {
        x: mm_to_i64(x),
        y: mm_to_i64(y),
    };
    Polygon64 {
        outer: vec![
            p(0.0, 0.0),
            p(20.0, 0.0),
            p(20.0, 10.0),
            p(10.0, 10.0),
            p(10.0, 20.0),
            p(0.0, 20.0),
        ],
        holes: Vec::new(),
    }
}

fn poly(points: &[(f64, f64)]) -> Polygon64 {
    Polygon64 {
        outer: points
            .iter()
            .map(|(x, y)| Point64 {
                x: mm_to_i64(*x),
                y: mm_to_i64(*y),
            })
            .collect(),
        holes: Vec::new(),
    }
}

// =====================================================================
// Correctness equivalence tests
// =====================================================================

#[derive(Debug, Clone)]
struct EqCase {
    label: &'static str,
    a: Polygon64,
    b: Polygon64,
    expect_collision: bool,
}

fn run_equivalence_tests() -> (usize, usize, Vec<String>) {
    let cases = vec![
        // Basic rectangle cases
        EqCase {
            label: "separated_rectangles",
            a: rect(0.0, 0.0, 10.0, 10.0),
            b: rect(20.0, 0.0, 10.0, 10.0),
            expect_collision: false,
        },
        EqCase {
            label: "clear_overlap",
            a: rect(0.0, 0.0, 10.0, 10.0),
            b: rect(5.0, 5.0, 10.0, 10.0),
            expect_collision: true,
        },
        EqCase {
            label: "edge_touch",
            a: rect(0.0, 0.0, 10.0, 10.0),
            b: rect(10.0, 0.0, 10.0, 10.0),
            expect_collision: true,
        },
        EqCase {
            label: "corner_touch",
            a: rect(0.0, 0.0, 10.0, 10.0),
            b: rect(10.0, 10.0, 10.0, 10.0),
            expect_collision: true,
        },
        EqCase {
            label: "containment",
            a: rect(0.0, 0.0, 20.0, 20.0),
            b: rect(5.0, 5.0, 5.0, 5.0),
            expect_collision: true,
        },
        EqCase {
            label: "concave_near_miss",
            a: concave_notch(),
            b: rect(12.0, 0.0, 5.0, 5.0),
            expect_collision: false,
        },
        EqCase {
            label: "concave_actual_overlap",
            a: concave_notch(),
            b: rect(8.0, 8.0, 5.0, 5.0),
            expect_collision: true,
        },
        EqCase {
            label: "point_touch_diagonal",
            a: rect(0.0, 0.0, 10.0, 10.0),
            b: rect(10.0, 5.0, 5.0, 5.0),
            expect_collision: true,
        },
        EqCase {
            label: "high_vertex_a",
            a: poly(&[
                (0.0, 0.0),
                (50.0, 0.0),
                (50.0, 10.0),
                (40.0, 10.0),
                (40.0, 20.0),
                (30.0, 20.0),
                (30.0, 30.0),
                (20.0, 30.0),
                (20.0, 40.0),
                (10.0, 40.0),
                (10.0, 50.0),
                (0.0, 50.0),
            ]),
            b: rect(5.0, 5.0, 5.0, 5.0),
            expect_collision: true,
        },
        EqCase {
            label: "high_vertex_near_miss",
            a: poly(&[
                (0.0, 0.0),
                (50.0, 0.0),
                (50.0, 10.0),
                (40.0, 10.0),
                (40.0, 20.0),
                (30.0, 20.0),
                (30.0, 30.0),
                (20.0, 30.0),
                (20.0, 40.0),
                (10.0, 40.0),
                (10.0, 50.0),
                (0.0, 50.0),
            ]),
            b: rect(51.0, 5.0, 5.0, 5.0),
            expect_collision: false,
        },
        EqCase {
            label: "triangle_inside_rect",
            a: rect(0.0, 0.0, 100.0, 100.0),
            b: poly(&[(30.0, 30.0), (70.0, 30.0), (50.0, 80.0)]),
            expect_collision: false,
        },
        EqCase {
            label: "triangle_overlaps_rect",
            a: rect(0.0, 0.0, 100.0, 100.0),
            b: poly(&[(10.0, 10.0), (150.0, 10.0), (50.0, 80.0)]),
            expect_collision: true,
        },
    ];

    let mut passed = 0;
    let mut failed = 0;
    let mut errors = Vec::new();

    for case in cases {
        let own_result = own_polygons_intersect_or_touch(&case.a, &case.b);
        let iovr_result =
            i_overlay_narrow::polygons_intersect_or_touch_i_overlay(&case.a, &case.b);

        let own_matches = own_result == case.expect_collision;
        let iovr_matches = iovr_result == case.expect_collision;
        let iovr_vs_own_consistent = !(own_result && !iovr_result); // no false accept

        if !own_matches || !iovr_matches || !iovr_vs_own_consistent {
            failed += 1;
            errors.push(format!(
                "[FAIL] {}: expect={} own={} iovr={} (own_match={} iovr_match={} iovr_vs_own_consistent={})",
                case.label,
                case.expect_collision,
                own_result,
                iovr_result,
                own_matches,
                iovr_matches,
                iovr_vs_own_consistent
            ));
        } else {
            passed += 1;
            println!(
                "[PASS] {}: own={} iovr={}",
                case.label, own_result, iovr_result
            );
        }
    }

    (passed, failed, errors)
}

// =====================================================================
// Microbenchmark
// =====================================================================

fn run_microbench(strategy: &str, pair_count: usize) {
    // Generate random-ish polygon pairs
    let mut pairs = Vec::with_capacity(pair_count);
    let mut rng_state = 42u64;
    for i in 0..pair_count {
        let seed = rng_state.wrapping_mul(6364136223846793005).wrapping_add(i as u64);
        let rx = (seed % 800) as f64 / 10.0;
        let ry = ((seed >> 16) % 600) as f64 / 10.0;
        let rw = 5.0 + ((seed >> 32) % 20) as f64;
        let rh = 5.0 + ((seed >> 48) % 20) as f64;
        let dx = 3.0 + ((seed % 50) as f64);
        let dy = 3.0 + (((seed >> 8) % 50) as f64);
        pairs.push((rect(rx, ry, rw, rh), rect(rx + dx, ry + dy, rw, rh)));
    }

    let start = Instant::now();
    let mut collisions = 0;
    let mut own_results = Vec::with_capacity(pair_count);
    for (a, b) in &pairs {
        let r = own_polygons_intersect_or_touch(a, b);
        if r {
            collisions += 1;
        }
        own_results.push(r);
    }
    let own_elapsed = start.elapsed();

    let start = Instant::now();
    let mut iovr_collisions = 0;
    let mut iovr_results = Vec::with_capacity(pair_count);
    for (a, b) in &pairs {
        let r = i_overlay_narrow::polygons_intersect_or_touch_i_overlay(a, b);
        if r {
            iovr_collisions += 1;
        }
        iovr_results.push(r);
    }
    let iovr_elapsed = start.elapsed();

    let mismatches: usize = own_results
        .iter()
        .zip(iovr_results.iter())
        .filter(|(o, i)| **o != **i)
        .count();

    let false_accepts: usize = own_results
        .iter()
        .zip(iovr_results.iter())
        .filter(|(o, i)| **o && !**i)
        .count();

    let conservative_rejects: usize = own_results
        .iter()
        .zip(iovr_results.iter())
        .filter(|(o, i)| !**o && **i)
        .count();

    let own_ns_pair = own_elapsed.as_nanos() as f64 / pair_count as f64;
    let iovr_ns_pair = iovr_elapsed.as_nanos() as f64 / pair_count as f64;

    println!();
    println!("========================================");
    println!(" MICROBENCHMARK RESULTS");
    println!("========================================");
    println!("Pair count:       {}", pair_count);
    println!("Strategy          own          i_overlay");
    println!("----------------------------------------");
    println!("Runtime ms:       {:.3}         {:.3}", own_elapsed.as_secs_f64() * 1000.0, iovr_elapsed.as_secs_f64() * 1000.0);
    println!("ns/pair:          {:.1}         {:.1}", own_ns_pair, iovr_ns_pair);
    println!("Collision count:  {}          {}", collisions, iovr_collisions);
    println!("Mismatch (own):   {} (= own says collision but iovr says no)", mismatches);
    println!("False accepts:    {} (own=collision, iovr=no_collision)", false_accepts);
    println!("Conservative:     {} (own=no_collision, iovr=collision)", conservative_rejects);
    println!("========================================");
    if false_accepts > 0 {
        println!("*** CRITICAL: {} FALSE ACCEPTS DETECTED ***", false_accepts);
    } else if mismatches > 0 {
        println!("Note: {} mismatches (conservative or informational)", mismatches);
    }
}

// =====================================================================
// Main
// =====================================================================

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut mode = "equivalence";
    let mut strategy = "both";
    let mut pairs = 1000usize;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--mode" => {
                if i + 1 < args.len() {
                    mode = &args[i + 1];
                    i += 2;
                } else {
                    i += 1;
                }
            }
            "--strategy" => {
                if i + 1 < args.len() {
                    strategy = &args[i + 1];
                    i += 2;
                } else {
                    i += 1;
                }
            }
            "--pairs" => {
                if i + 1 < args.len() {
                    pairs = args[i + 1].parse().unwrap_or(1000);
                    i += 2;
                } else {
                    i += 1;
                }
            }
            _ => i += 1,
        }
    }

    println!("T06M NARROW-PHASE STRATEGY BENCH");
    println!("Mode: {}, Strategy: {}, Pairs: {}", mode, strategy, pairs);

    match mode {
        "equivalence" => {
            println!("\n=== CORRECTNESS EQUIVALENCE TESTS ===");
            let (passed, failed, errors) = run_equivalence_tests();
            println!("\nResults: {} passed, {} failed", passed, failed);
            for err in &errors {
                println!("{}", err);
            }
            if failed == 0 {
                println!("\nAll correctness tests PASSED");
            } else {
                println!("\n{} correctness tests FAILED", failed);
                std::process::exit(1);
            }
        }
        "microbench" => {
            run_microbench(strategy, pairs);
        }
        "both" => {
            println!("\n=== CORRECTNESS EQUIVALENCE TESTS ===");
            let (passed, failed, errors) = run_equivalence_tests();
            println!("\nResults: {} passed, {} failed", passed, failed);
            for err in &errors {
                println!("{}", err);
            }
            if failed > 0 {
                std::process::exit(1);
            }
            println!("\n=== MICROBENCHMARK ===");
            run_microbench(strategy, pairs);
        }
        _ => {
            eprintln!("Unknown mode: {}", mode);
            std::process::exit(1);
        }
    }
}