use std::collections::BTreeMap;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::geometry::scale::{i64_to_mm, mm_to_i64};
use crate::multi_bin::greedy::{CompactionMode, MultiSheetResult, OccupiedExtentI64};
use crate::placement::blf::PlacedItem;

pub fn build_output_v2(
    seed: u64,
    _elapsed_sec: f64,
    utilization_pct: f64,
    result: &MultiSheetResult,
) -> Value {
    let mut placements = result.placed.clone();
    placements.sort_by(|a, b| {
        a.sheet
            .cmp(&b.sheet)
            .then(a.part_id.cmp(&b.part_id))
            .then(a.instance.cmp(&b.instance))
    });

    let placements_json: Vec<Value> = placements
        .iter()
        .map(|p| {
            json!({
                "part_id": p.part_id,
                "instance": p.instance,
                "sheet": p.sheet,
                "x_mm": p.x_mm,
                "y_mm": p.y_mm,
                "rotation_deg": p.rotation_deg
            })
        })
        .collect();

    let unplaced_json: Vec<Value> = result
        .unplaced
        .iter()
        .map(|u| {
            json!({
                "part_id": u.part_id,
                "instance": u.instance,
                "reason": u.reason
            })
        })
        .collect();

    let status = if result.unplaced.is_empty() {
        "ok"
    } else {
        "partial"
    };
    let determinism_hash = compute_determinism_hash(&placements);
    let compaction_mode = match result.compaction.mode {
        CompactionMode::Off => "off",
        CompactionMode::Slide => "slide",
    };

    json!({
        "version": "nesting_engine_v2",
        "seed": seed,
        "solver_version": env!("CARGO_PKG_VERSION"),
        "status": status,
        "sheets_used": result.sheets_used,
        "placements": placements_json,
        "unplaced": unplaced_json,
        "objective": {
            "sheets_used": result.sheets_used,
            "utilization_pct": utilization_pct,
            "remnant_value_ppm": result.remnant_value_ppm,
            "remnant_area_score_ppm": result.remnant_area_score_ppm,
            "remnant_compactness_score_ppm": result.remnant_compactness_score_ppm,
            "remnant_min_width_score_ppm": result.remnant_min_width_score_ppm
        },
        "meta": {
            "determinism_hash": determinism_hash,
            "compaction": {
                "mode": compaction_mode,
                "applied": result.compaction.applied,
                "moved_items_count": result.compaction.moved_items_count,
                "occupied_extent_before": occupied_extent_to_json(result.compaction.occupied_extent_before),
                "occupied_extent_after": occupied_extent_to_json(result.compaction.occupied_extent_after)
            }
        }
    })
}

fn occupied_extent_to_json(extent: Option<OccupiedExtentI64>) -> Value {
    let Some(extent) = extent else {
        return Value::Null;
    };
    let min_x = i64_to_mm(extent.min_x);
    let min_y = i64_to_mm(extent.min_y);
    let max_x = i64_to_mm(extent.max_x);
    let max_y = i64_to_mm(extent.max_y);
    json!({
        "min_x_mm": min_x,
        "min_y_mm": min_y,
        "max_x_mm": max_x,
        "max_y_mm": max_y,
        "width_mm": max_x - min_x,
        "height_mm": max_y - min_y
    })
}

fn hash_view_v1_canonical_json_bytes(placements: &[PlacedItem]) -> String {
    let mut hv_placements: Vec<(String, BTreeMap<String, Value>)> = placements
        .iter()
        .map(|p| {
            let sheet_id = format!("S{}", p.sheet);
            let mut item = BTreeMap::new();
            item.insert("part_id".to_string(), Value::String(p.part_id.clone()));
            item.insert("rotation_deg".to_string(), Value::from(p.rotation_deg));
            item.insert("sheet_id".to_string(), Value::String(sheet_id.clone()));
            item.insert("x_scaled_i64".to_string(), Value::from(mm_to_i64(p.x_mm)));
            item.insert("y_scaled_i64".to_string(), Value::from(mm_to_i64(p.y_mm)));
            (sheet_id, item)
        })
        .collect();

    hv_placements.sort_by(|(_, a), (_, b)| {
        let sa = a.get("sheet_id").and_then(Value::as_str).unwrap_or("");
        let sb = b.get("sheet_id").and_then(Value::as_str).unwrap_or("");
        let pa = a.get("part_id").and_then(Value::as_str).unwrap_or("");
        let pb = b.get("part_id").and_then(Value::as_str).unwrap_or("");
        let ra = a
            .get("rotation_deg")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        let rb = b
            .get("rotation_deg")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        let xa = a
            .get("x_scaled_i64")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        let xb = b
            .get("x_scaled_i64")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        let ya = a
            .get("y_scaled_i64")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        let yb = b
            .get("y_scaled_i64")
            .and_then(Value::as_i64)
            .unwrap_or_default();
        sa.cmp(sb)
            .then(pa.cmp(pb))
            .then(ra.cmp(&rb))
            .then(xa.cmp(&xb))
            .then(ya.cmp(&yb))
    });

    let placements_values: Vec<Value> = hv_placements
        .into_iter()
        .map(|(_, map)| {
            let mut obj = serde_json::Map::new();
            for (k, v) in map {
                obj.insert(k, v);
            }
            Value::Object(obj)
        })
        .collect();

    let mut hash_view = BTreeMap::new();
    hash_view.insert("placements".to_string(), Value::Array(placements_values));
    hash_view.insert(
        "schema_version".to_string(),
        Value::String("nesting_engine.hash_view.v1".to_string()),
    );

    // Repo-native canonical bytes contract: compact JSON + key-sorted objects.
    serde_json::to_string(&hash_view).unwrap_or_else(|_| "{}".to_string())
}

fn compute_determinism_hash(placements: &[PlacedItem]) -> String {
    let canonical = hash_view_v1_canonical_json_bytes(placements);
    let digest = Sha256::digest(canonical.as_bytes());
    format!("sha256:{}", hex::encode(digest))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_bin::greedy::{CompactionEvidence, CompactionMode, MultiSheetResult};
    use crate::placement::blf::{PlacedItem, UnplacedItem};

    #[test]
    fn determinism_hash_is_stable() {
        let res = MultiSheetResult {
            placed: vec![PlacedItem {
                part_id: "a".to_string(),
                instance: 0,
                sheet: 0,
                x_mm: 1.0,
                y_mm: 2.0,
                rotation_deg: 0,
            }],
            unplaced: vec![UnplacedItem {
                part_id: "b".to_string(),
                instance: 0,
                reason: "PART_NEVER_FITS_SHEET".to_string(),
            }],
            sheets_used: 1,
            remnant_value_ppm: 742_000,
            remnant_area_score_ppm: 380_000,
            remnant_compactness_score_ppm: 900_000,
            remnant_min_width_score_ppm: 700_000,
            compaction: CompactionEvidence {
                mode: CompactionMode::Off,
                applied: false,
                moved_items_count: 0,
                occupied_extent_before: None,
                occupied_extent_after: None,
            },
        };

        let a = build_output_v2(42, 0.1, 12.0, &res);
        let b = build_output_v2(42, 0.1, 12.0, &res);
        assert_eq!(
            a["meta"]["determinism_hash"], b["meta"]["determinism_hash"],
            "determinism hash changed for identical input"
        );
    }

    #[test]
    fn determinism_full_output_json_is_byte_identical() {
        let res = MultiSheetResult {
            placed: vec![PlacedItem {
                part_id: "a".to_string(),
                instance: 0,
                sheet: 0,
                x_mm: 1.0,
                y_mm: 2.0,
                rotation_deg: 0,
            }],
            unplaced: vec![UnplacedItem {
                part_id: "b".to_string(),
                instance: 0,
                reason: "PART_NEVER_FITS_SHEET".to_string(),
            }],
            sheets_used: 1,
            remnant_value_ppm: 742_000,
            remnant_area_score_ppm: 380_000,
            remnant_compactness_score_ppm: 900_000,
            remnant_min_width_score_ppm: 700_000,
            compaction: CompactionEvidence {
                mode: CompactionMode::Off,
                applied: false,
                moved_items_count: 0,
                occupied_extent_before: None,
                occupied_extent_after: None,
            },
        };

        let first = serde_json::to_string(&build_output_v2(42, 0.1, 12.0, &res))
            .expect("first output JSON must serialize");
        let second = serde_json::to_string(&build_output_v2(42, 0.1, 12.0, &res))
            .expect("second output JSON must serialize");
        assert_eq!(
            first, second,
            "full output JSON bytes changed for identical input"
        );
    }

    #[test]
    fn determinism_hash_view_v1_canonical_json_is_byte_identical() {
        let placements = vec![
            PlacedItem {
                part_id: "b".to_string(),
                instance: 1,
                sheet: 1,
                x_mm: 0.0,
                y_mm: 0.0,
                rotation_deg: 90,
            },
            PlacedItem {
                part_id: "a".to_string(),
                instance: 2,
                sheet: 0,
                x_mm: 1.0,
                y_mm: 2.0,
                rotation_deg: 0,
            },
            PlacedItem {
                part_id: "a".to_string(),
                instance: 0,
                sheet: 0,
                x_mm: 0.0,
                y_mm: 0.0,
                rotation_deg: 0,
            },
        ];

        let canonical = hash_view_v1_canonical_json_bytes(&placements);
        let expected = "{\"placements\":[{\"part_id\":\"a\",\"rotation_deg\":0,\"sheet_id\":\"S0\",\"x_scaled_i64\":0,\"y_scaled_i64\":0},{\"part_id\":\"a\",\"rotation_deg\":0,\"sheet_id\":\"S0\",\"x_scaled_i64\":1000000,\"y_scaled_i64\":2000000},{\"part_id\":\"b\",\"rotation_deg\":90,\"sheet_id\":\"S1\",\"x_scaled_i64\":0,\"y_scaled_i64\":0}],\"schema_version\":\"nesting_engine.hash_view.v1\"}";
        assert_eq!(
            canonical, expected,
            "canonical hash-view JSON bytes changed unexpectedly"
        );
    }

    #[test]
    fn remnant_objective_is_exposed_in_output_v2() {
        let res = MultiSheetResult {
            placed: vec![PlacedItem {
                part_id: "a".to_string(),
                instance: 0,
                sheet: 0,
                x_mm: 0.0,
                y_mm: 0.0,
                rotation_deg: 0,
            }],
            unplaced: vec![],
            sheets_used: 1,
            remnant_value_ppm: 742_000,
            remnant_area_score_ppm: 380_000,
            remnant_compactness_score_ppm: 900_000,
            remnant_min_width_score_ppm: 700_000,
            compaction: CompactionEvidence {
                mode: CompactionMode::Off,
                applied: false,
                moved_items_count: 0,
                occupied_extent_before: None,
                occupied_extent_after: None,
            },
        };

        let out = build_output_v2(1, 0.0, 87.5, &res);
        assert_eq!(out["objective"]["remnant_value_ppm"], 742_000);
        assert_eq!(out["objective"]["remnant_area_score_ppm"], 380_000);
        assert_eq!(out["objective"]["remnant_compactness_score_ppm"], 900_000);
        assert_eq!(out["objective"]["remnant_min_width_score_ppm"], 700_000);
    }

    #[test]
    fn compaction_meta_is_exposed_in_output_v2() {
        let res = MultiSheetResult {
            placed: vec![PlacedItem {
                part_id: "a".to_string(),
                instance: 0,
                sheet: 0,
                x_mm: 0.0,
                y_mm: 0.0,
                rotation_deg: 0,
            }],
            unplaced: vec![],
            sheets_used: 1,
            remnant_value_ppm: 1,
            remnant_area_score_ppm: 1,
            remnant_compactness_score_ppm: 1,
            remnant_min_width_score_ppm: 1,
            compaction: CompactionEvidence {
                mode: CompactionMode::Slide,
                applied: true,
                moved_items_count: 2,
                occupied_extent_before: Some(crate::multi_bin::greedy::OccupiedExtentI64 {
                    min_x: 0,
                    min_y: 0,
                    max_x: 20_000_000,
                    max_y: 10_000_000,
                }),
                occupied_extent_after: Some(crate::multi_bin::greedy::OccupiedExtentI64 {
                    min_x: 0,
                    min_y: 0,
                    max_x: 18_000_000,
                    max_y: 9_000_000,
                }),
            },
        };

        let out = build_output_v2(1, 0.0, 10.0, &res);
        assert_eq!(out["meta"]["compaction"]["mode"], "slide");
        assert_eq!(out["meta"]["compaction"]["applied"], true);
        assert_eq!(out["meta"]["compaction"]["moved_items_count"], 2);
        assert_eq!(
            out["meta"]["compaction"]["occupied_extent_before"]["width_mm"],
            20.0
        );
        assert_eq!(
            out["meta"]["compaction"]["occupied_extent_after"]["width_mm"],
            18.0
        );
    }
}
