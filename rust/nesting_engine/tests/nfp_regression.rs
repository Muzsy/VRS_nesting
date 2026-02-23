use std::fs;
use std::path::{Path, PathBuf};

use nesting_engine::geometry::types::{signed_area2_i128, Point64, Polygon64};
use nesting_engine::nfp::convex::compute_convex_nfp;
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Fixture {
    description: String,
    polygon_a: Vec<[i64; 2]>,
    polygon_b: Vec<[i64; 2]>,
    rotation_deg_b: i64,
    expected_nfp: Vec<[i64; 2]>,
    expected_vertex_count: usize,
}

#[test]
fn fixture_library_passes() {
    let fixture_dir = fixture_dir();
    let mut fixture_files: Vec<PathBuf> = fs::read_dir(&fixture_dir)
        .expect("read fixture dir")
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("json"))
        .collect();
    fixture_files.sort();

    assert!(
        fixture_files.len() >= 2,
        "expected at least 2 fixture files in {}",
        fixture_dir.display()
    );

    for fixture_path in fixture_files {
        let fixture = read_fixture(&fixture_path);
        assert_eq!(
            fixture.rotation_deg_b, 0,
            "F2-1 fixtures should use 0° rotation: {}",
            fixture.description
        );

        let poly_a = to_polygon(&fixture.polygon_a);
        let poly_b = to_polygon(&fixture.polygon_b);
        let expected = to_points(&fixture.expected_nfp);

        let nfp_first =
            compute_convex_nfp(&poly_a, &poly_b).expect("fixture must produce convex NFP");
        let nfp_second =
            compute_convex_nfp(&poly_a, &poly_b).expect("fixture must produce convex NFP");

        assert_eq!(
            nfp_first.outer.len(),
            fixture.expected_vertex_count,
            "vertex count mismatch in fixture {}",
            fixture_path.display()
        );
        assert_eq!(
            canonicalize_ring(&nfp_first.outer),
            canonicalize_ring(&expected),
            "NFP mismatch in fixture {}",
            fixture_path.display()
        );
        assert_eq!(
            canonicalize_ring(&nfp_first.outer),
            canonicalize_ring(&nfp_second.outer),
            "NFP is not deterministic in fixture {}",
            fixture_path.display()
        );
    }
}

fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../poc/nfp_regression")
        .to_path_buf()
}

fn read_fixture(path: &Path) -> Fixture {
    let body = fs::read_to_string(path).expect("read fixture JSON");
    serde_json::from_str(&body).expect("parse fixture JSON")
}

fn to_polygon(points: &[[i64; 2]]) -> Polygon64 {
    Polygon64 {
        outer: to_points(points),
        holes: Vec::new(),
    }
}

fn to_points(points: &[[i64; 2]]) -> Vec<Point64> {
    points
        .iter()
        .map(|p| Point64 { x: p[0], y: p[1] })
        .collect()
}

fn canonicalize_ring(points: &[Point64]) -> Vec<Point64> {
    let mut normalized = points.to_vec();
    if normalized.len() > 1 && normalized.first() == normalized.last() {
        normalized.pop();
    }
    if normalized.is_empty() {
        return normalized;
    }

    if signed_area2_i128(&normalized) < 0 {
        normalized.reverse();
    }

    let start_idx = normalized
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
        .map(|(idx, _)| idx)
        .expect("non-empty ring");

    normalized.rotate_left(start_idx);
    normalized
}
