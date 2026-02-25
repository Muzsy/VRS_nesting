use std::fs;
use std::path::Path;

use nesting_engine::geometry::types::{Point64, Polygon64};
use nesting_engine::nfp::concave::{
    collect_orbit_next_event_trace, ConcaveNfpMode, ConcaveNfpOptions,
};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct Fixture {
    polygon_a: Vec<[i64; 2]>,
    polygon_b: Vec<[i64; 2]>,
}

#[test]
fn orbit_trace_prefix_is_stable_on_concave_fixtures() {
    let touching_group_trace = trace_prefix("concave_touching_group.json");
    assert_trace_prefix(
        "concave_touching_group.json",
        &touching_group_trace,
        &[
            ExpectedStep {
                step_index: 0,
                touching_group_signature: "a0:b0@-3,0|a0:b1@0,0|a7:b0@-3,0|a7:b1@0,0|a7:b2@-2,1",
                dx: 1,
                dy: 0,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 11,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|1,0|src0|a0|b0];event[vertex_b_to_edge_a|v0|e1]",
            },
            ExpectedStep {
                step_index: 1,
                touching_group_signature: "a0:b0@0,0|a0:b5@0,0|a1:b0@8,0|a1:b5@8,0|a2:b5@4,2",
                dx: 0,
                dy: 1,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 2,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|0,1|src0|a1|b0];event[vertex_b_to_edge_a|v0|e2]",
            },
            ExpectedStep {
                step_index: 2,
                touching_group_signature:
                    "a1:b0@8,0|a1:b5@8,0|a2:b0@4,2|a2:b5@4,2|a4:b4@4,6|a4:b5@4,6|a5:b4@8,6|a5:b5@8,2",
                dx: 0,
                dy: 1,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 2,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|0,1|src0|a1|b0];event[vertex_b_to_edge_a|v5|e6]",
            },
        ],
    );

    let multi_contact_trace = trace_prefix("concave_multi_contact.json");
    assert_trace_prefix(
        "concave_multi_contact.json",
        &multi_contact_trace,
        &[
            ExpectedStep {
                step_index: 0,
                touching_group_signature:
                    "a0:b0@-5,0|a0:b1@0,0|a11:b0@-5,0|a11:b1@0,0|a11:b2@-2,1",
                dx: 1,
                dy: 0,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 13,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|1,0|src0|a0|b0];event[vertex_b_to_edge_a|v0|e1]",
            },
            ExpectedStep {
                step_index: 1,
                touching_group_signature:
                    "a0:b0@0,0|a0:b11@0,0|a1:b0@8,0|a1:b10@8,0|a1:b11@8,0",
                dx: 0,
                dy: 1,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 1,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|0,1|src0|a1|b0];event[vertex_b_to_edge_a|v11|e2]",
            },
            ExpectedStep {
                step_index: 2,
                touching_group_signature:
                    "a1:b0@8,0|a1:b10@8,0|a1:b11@8,0|a2:b10@6,2|a2:b11@6,2",
                dx: 0,
                dy: 1,
                next_event_kind: "vertex_b_to_edge_a",
                t_num: 1,
                t_den: 1,
                tie_break_reason:
                    "dir[q0|0,1|src0|a1|b0];event[vertex_b_to_edge_a|v0|e2]",
            },
        ],
    );
}

struct ExpectedStep {
    step_index: usize,
    touching_group_signature: &'static str,
    dx: i64,
    dy: i64,
    next_event_kind: &'static str,
    t_num: i128,
    t_den: i128,
    tie_break_reason: &'static str,
}

fn trace_prefix(fixture_name: &str) -> nesting_engine::nfp::concave::OrbitNextEventTrace {
    let fixture = read_fixture(fixture_name);
    let a = to_polygon(&fixture.polygon_a);
    let b = to_polygon(&fixture.polygon_b);
    collect_orbit_next_event_trace(
        &a,
        &b,
        ConcaveNfpOptions {
            mode: ConcaveNfpMode::ExactOrbit,
            max_steps: 8,
            enable_fallback: false,
        },
        3,
    )
    .expect("trace collection must succeed")
}

fn assert_trace_prefix(
    fixture_name: &str,
    trace: &nesting_engine::nfp::concave::OrbitNextEventTrace,
    expected: &[ExpectedStep],
) {
    assert!(
        trace.steps.len() >= expected.len(),
        "trace length mismatch for {}: expected at least {}, got {}",
        fixture_name,
        expected.len(),
        trace.steps.len()
    );

    for (idx, expected_step) in expected.iter().enumerate() {
        let actual = &trace.steps[idx];
        assert_eq!(
            actual.step_index, expected_step.step_index,
            "step_index mismatch in {} at prefix index {}",
            fixture_name, idx
        );
        assert_eq!(
            actual.touching_group_signature, expected_step.touching_group_signature,
            "touching_group_signature mismatch in {} at step {}",
            fixture_name, actual.step_index
        );
        assert_eq!(
            (actual.chosen_direction.dx, actual.chosen_direction.dy),
            (expected_step.dx, expected_step.dy),
            "chosen_direction mismatch in {} at step {}",
            fixture_name, actual.step_index
        );
        assert_eq!(
            actual.next_event_kind, expected_step.next_event_kind,
            "next_event_kind mismatch in {} at step {}",
            fixture_name, actual.step_index
        );
        assert_eq!(
            (actual.next_event_t_num, actual.next_event_t_den),
            (expected_step.t_num, expected_step.t_den),
            "next_event_t mismatch in {} at step {}",
            fixture_name, actual.step_index
        );
        assert_eq!(
            actual.tie_break_reason, expected_step.tie_break_reason,
            "tie_break_reason mismatch in {} at step {}",
            fixture_name, actual.step_index
        );
    }
}

fn read_fixture(name: &str) -> Fixture {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../poc/nfp_regression")
        .join(name);
    let body = fs::read_to_string(path).expect("read fixture JSON");
    serde_json::from_str(&body).expect("parse fixture JSON")
}

fn to_polygon(points: &[[i64; 2]]) -> Polygon64 {
    Polygon64 {
        outer: points
            .iter()
            .map(|p| Point64 { x: p[0], y: p[1] })
            .collect(),
        holes: Vec::new(),
    }
}
