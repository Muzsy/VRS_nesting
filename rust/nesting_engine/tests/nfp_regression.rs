use std::fs;
use std::path::{Path, PathBuf};

use nesting_engine::geometry::types::{is_ccw, is_convex, signed_area2_i128, Point64, Polygon64};
use nesting_engine::nfp::boundary_clean::ring_has_self_intersection;
use nesting_engine::nfp::concave::{
    compute_concave_nfp, compute_concave_nfp_default, ConcaveNfpMode, ConcaveNfpOptions,
};
use nesting_engine::nfp::convex::{compute_convex_nfp, compute_convex_nfp_reference};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Fixture {
    description: String,
    #[serde(default)]
    fixture_type: Option<String>,
    polygon_a: Vec<[i64; 2]>,
    polygon_b: Vec<[i64; 2]>,
    rotation_deg_b: i64,
    expected_nfp: Vec<[i64; 2]>,
    expected_vertex_count: usize,
    #[serde(default)]
    prefer_exact: Option<bool>,
    #[serde(default)]
    allow_exact_equals_stable: Option<bool>,
    #[serde(default)]
    expect_exact_error: Option<bool>,
    #[serde(default)]
    expect_exact_fallback: Option<bool>,
}

#[test]
fn convex_fixture_library_passes() {
    let fixture_files = fixture_files();
    let convex_files: Vec<PathBuf> = fixture_files
        .into_iter()
        .filter(|path| !is_concave_fixture(path, &read_fixture(path)))
        .collect();

    assert!(
        convex_files.len() >= 7,
        "expected at least 7 convex fixtures in {}",
        fixture_dir().display()
    );

    for fixture_path in convex_files {
        let fixture = read_fixture(&fixture_path);
        assert_eq!(
            fixture.rotation_deg_b, 0,
            "convex fixtures should use 0 degree rotation: {}",
            fixture.description
        );

        let poly_a = to_polygon(&fixture.polygon_a);
        let poly_b = to_polygon(&fixture.polygon_b);
        let expected = to_points(&fixture.expected_nfp);

        assert!(
            is_convex(&poly_a.outer) && is_ccw(&poly_a.outer),
            "fixture polygon_a must be convex + CCW in fixture {}",
            fixture_path.display()
        );
        assert!(
            is_convex(&poly_b.outer) && is_ccw(&poly_b.outer),
            "fixture polygon_b must be convex + CCW in fixture {}",
            fixture_path.display()
        );

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

#[test]
fn concave_fixture_library_passes() {
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum PreferExactOutcome {
        ExactClosed,
        ExpectedExactError,
    }

    let fixture_files = fixture_files();
    let concave_files: Vec<PathBuf> = fixture_files
        .into_iter()
        .filter(|path| is_concave_fixture(path, &read_fixture(path)))
        .collect();

    assert!(
        concave_files.len() >= 5,
        "expected at least 5 concave fixtures in {}",
        fixture_dir().display()
    );

    let mut exact_preferred_fixture_count = 0usize;
    let mut exact_preferred_evidence_count = 0usize;

    for fixture_path in concave_files {
        let fixture = read_fixture(&fixture_path);
        let prefer_exact = fixture.prefer_exact.unwrap_or(false);
        let allow_exact_equals_stable = fixture.allow_exact_equals_stable.unwrap_or(false);
        let expect_exact_error = fixture.expect_exact_error.unwrap_or(false);
        let expect_exact_fallback = fixture.expect_exact_fallback.unwrap_or(false);
        assert!(
            !(allow_exact_equals_stable && expect_exact_error),
            "fixture cannot allow equal exact/stable and expect exact error simultaneously: {}",
            fixture_path.display()
        );
        assert!(
            !(prefer_exact && expect_exact_fallback),
            "fixture cannot require exact-no-fallback and fallback simultaneously: {}",
            fixture_path.display()
        );

        assert_eq!(
            fixture.rotation_deg_b, 0,
            "concave fixtures should use 0 degree rotation: {}",
            fixture.description
        );

        let poly_a = to_polygon(&fixture.polygon_a);
        let poly_b = to_polygon(&fixture.polygon_b);
        let expected = to_points(&fixture.expected_nfp);

        assert!(
            !is_convex(&poly_a.outer) || !is_convex(&poly_b.outer),
            "at least one polygon must be concave in fixture {}",
            fixture_path.display()
        );

        let stable_first =
            compute_concave_nfp_default(&poly_a, &poly_b).expect("stable concave path must work");
        let stable_second =
            compute_concave_nfp_default(&poly_a, &poly_b).expect("stable concave path must work");

        assert_eq!(
            stable_first.outer.len(),
            fixture.expected_vertex_count,
            "vertex count mismatch in fixture {}",
            fixture_path.display()
        );
        assert_eq!(
            canonicalize_ring(&stable_first.outer),
            canonicalize_ring(&expected),
            "stable concave NFP mismatch in fixture {}",
            fixture_path.display()
        );
        assert_eq!(
            canonicalize_ring(&stable_first.outer),
            canonicalize_ring(&stable_second.outer),
            "stable concave NFP is not deterministic in fixture {}",
            fixture_path.display()
        );
        assert!(
            !ring_has_self_intersection(&stable_first.outer),
            "stable concave boundary is self intersecting in fixture {}",
            fixture_path.display()
        );

        if prefer_exact {
            exact_preferred_fixture_count += 1;
            let exact_first = compute_concave_nfp(
                &poly_a,
                &poly_b,
                ConcaveNfpOptions {
                    mode: ConcaveNfpMode::ExactOrbit,
                    max_steps: 4096,
                    enable_fallback: false,
                },
            );

            if expect_exact_error {
                let err = exact_first.unwrap_err();
                assert!(
                    matches!(
                        err,
                        nesting_engine::nfp::NfpError::OrbitLoopDetected
                            | nesting_engine::nfp::NfpError::OrbitDeadEnd
                            | nesting_engine::nfp::NfpError::OrbitMaxStepsReached
                            | nesting_engine::nfp::NfpError::OrbitNotClosed
                    ),
                    "prefer_exact fixture {} must fail with explicit orbit error",
                    fixture_path.display()
                );
                let outcome = PreferExactOutcome::ExpectedExactError;
                assert_eq!(outcome, PreferExactOutcome::ExpectedExactError);
                exact_preferred_evidence_count += 1;
            } else {
                let exact_first = exact_first.unwrap_or_else(|err| {
                    panic!(
                        "exact mode without fallback must succeed in fixture {}: {:?}",
                        fixture_path.display(),
                        err
                    )
                });
                let exact_second = compute_concave_nfp(
                    &poly_a,
                    &poly_b,
                    ConcaveNfpOptions {
                        mode: ConcaveNfpMode::ExactOrbit,
                        max_steps: 4096,
                        enable_fallback: false,
                    },
                )
                .unwrap_or_else(|err| {
                    panic!(
                        "exact mode second run failed in fixture {}: {:?}",
                        fixture_path.display(),
                        err
                    )
                });

                let exact_ring = canonicalize_ring(&exact_first.outer);
                let exact_ring_second = canonicalize_ring(&exact_second.outer);
                let stable_ring = canonicalize_ring(&stable_first.outer);

                assert_eq!(
                    exact_ring,
                    exact_ring_second,
                    "exact no-fallback mode is not deterministic in fixture {}",
                    fixture_path.display()
                );
                assert!(
                    !ring_has_self_intersection(&exact_first.outer),
                    "exact no-fallback boundary is self intersecting in fixture {}",
                    fixture_path.display()
                );
                if !allow_exact_equals_stable {
                    assert_ne!(
                        exact_ring,
                        stable_ring,
                        "prefer_exact fixture {} must prove ExactClosed by differing from stable ring",
                        fixture_path.display()
                    );
                }
                let outcome = PreferExactOutcome::ExactClosed;
                assert_eq!(outcome, PreferExactOutcome::ExactClosed);
                exact_preferred_evidence_count += 1;
            }
        }

        if expect_exact_fallback {
            let exact = compute_concave_nfp(
                &poly_a,
                &poly_b,
                ConcaveNfpOptions {
                    mode: ConcaveNfpMode::ExactOrbit,
                    max_steps: 1,
                    enable_fallback: true,
                },
            )
            .expect("exact mode with fallback must return a valid result");

            assert_eq!(
                canonicalize_ring(&exact.outer),
                canonicalize_ring(&stable_first.outer),
                "exact+fallback output mismatch in fixture {}",
                fixture_path.display()
            );
            assert!(
                !ring_has_self_intersection(&exact.outer),
                "exact+fallback boundary is self intersecting in fixture {}",
                fixture_path.display()
            );
        }
    }

    assert!(
        exact_preferred_fixture_count >= 3,
        "at least 3 concave fixtures must opt into exact-no-fallback coverage"
    );
    assert!(
        exact_preferred_evidence_count >= 3,
        "prefer_exact evidence (ExactClosed or expected exact error) must exist on at least 3 fixtures"
    );
}

#[test]
fn edge_merge_equals_hull_on_all_convex_fixtures() {
    let fixture_files = fixture_files();
    let convex_files: Vec<PathBuf> = fixture_files
        .into_iter()
        .filter(|path| !is_concave_fixture(path, &read_fixture(path)))
        .collect();

    assert!(
        convex_files.len() >= 7,
        "expected at least 7 convex fixtures in {}",
        fixture_dir().display()
    );

    for fixture_path in convex_files {
        let fixture = read_fixture(&fixture_path);
        let poly_a = to_polygon(&fixture.polygon_a);
        let poly_b = to_polygon(&fixture.polygon_b);

        assert!(
            is_convex(&poly_a.outer) && is_ccw(&poly_a.outer),
            "fixture polygon_a must be convex + CCW in fixture {}",
            fixture_path.display()
        );
        assert!(
            is_convex(&poly_b.outer) && is_ccw(&poly_b.outer),
            "fixture polygon_b must be convex + CCW in fixture {}",
            fixture_path.display()
        );

        let edge_result =
            compute_convex_nfp(&poly_a, &poly_b).expect("edge-merge path must succeed");
        let hull_result =
            compute_convex_nfp_reference(&poly_a, &poly_b).expect("hull path must succeed");

        assert_eq!(
            canonicalize_ring(&edge_result.outer),
            canonicalize_ring(&hull_result.outer),
            "edge-merge != hull on fixture {} ({})",
            fixture_path.display(),
            fixture.description
        );
    }
}

fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../poc/nfp_regression")
        .to_path_buf()
}

fn fixture_files() -> Vec<PathBuf> {
    let mut fixture_files: Vec<PathBuf> = fs::read_dir(fixture_dir())
        .expect("read fixture dir")
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("json"))
        .collect();
    fixture_files.sort();
    fixture_files
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

fn is_concave_fixture(path: &Path, fixture: &Fixture) -> bool {
    if let Some(fixture_type) = &fixture.fixture_type {
        if fixture_type.eq_ignore_ascii_case("concave") {
            return true;
        }
    }

    path.file_name()
        .and_then(|name| name.to_str())
        .map(|name| name.starts_with("concave_"))
        .unwrap_or(false)
}
