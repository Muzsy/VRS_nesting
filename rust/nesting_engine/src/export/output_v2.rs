use std::collections::BTreeMap;

use serde_json::{Value, json};
use sha2::{Digest, Sha256};

use crate::geometry::scale::mm_to_i64;
use crate::multi_bin::greedy::MultiSheetResult;
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

    let status = if result.unplaced.is_empty() { "ok" } else { "partial" };
    let determinism_hash = compute_determinism_hash(&placements);

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
            "determinism_hash": determinism_hash
        }
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
        let ra = a.get("rotation_deg").and_then(Value::as_i64).unwrap_or_default();
        let rb = b.get("rotation_deg").and_then(Value::as_i64).unwrap_or_default();
        let xa = a.get("x_scaled_i64").and_then(Value::as_i64).unwrap_or_default();
        let xb = b.get("x_scaled_i64").and_then(Value::as_i64).unwrap_or_default();
        let ya = a.get("y_scaled_i64").and_then(Value::as_i64).unwrap_or_default();
        let yb = b.get("y_scaled_i64").and_then(Value::as_i64).unwrap_or_default();
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
    hash_view.insert(
        "placements".to_string(),
        Value::Array(placements_values),
    );
    hash_view.insert(
        "schema_version".to_string(),
        Value::String("nesting_engine.hash_view.v1".to_string()),
    );

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
    use crate::multi_bin::greedy::MultiSheetResult;
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
        };

        let a = build_output_v2(42, 0.1, 12.0, &res);
        let b = build_output_v2(42, 0.1, 12.0, &res);
        assert_eq!(
            a["meta"]["determinism_hash"],
            b["meta"]["determinism_hash"],
            "determinism hash changed for identical input"
        );
    }

    #[test]
    fn hash_view_v1_canonical_json_is_byte_identical() {
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
        };

        let out = build_output_v2(1, 0.0, 87.5, &res);
        assert_eq!(out["objective"]["remnant_value_ppm"], 742_000);
        assert_eq!(out["objective"]["remnant_area_score_ppm"], 380_000);
        assert_eq!(out["objective"]["remnant_compactness_score_ppm"], 900_000);
        assert_eq!(out["objective"]["remnant_min_width_score_ppm"], 700_000);
    }
}
