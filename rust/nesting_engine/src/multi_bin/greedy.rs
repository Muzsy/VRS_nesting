use std::collections::BTreeMap;
use std::time::Instant;

use crate::geometry::types::Polygon64;
use crate::placement::blf::{InflatedPartSpec, UnplacedItem};
use crate::placement::{PlacedItem, PlacementResult, blf_place, nfp_place};
use nesting_engine::nfp::cache::NfpCache;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlacerKind {
    Blf,
    Nfp,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MultiSheetResult {
    pub placed: Vec<PlacedItem>,
    pub unplaced: Vec<UnplacedItem>,
    pub sheets_used: usize,
}

pub fn greedy_multi_sheet(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    time_limit_sec: u64,
    placer_kind: PlacerKind,
) -> MultiSheetResult {
    let started_at = Instant::now();
    let mut nfp_cache = NfpCache::new();
    let mut sheet_index = 0usize;
    let mut placed: Vec<PlacedItem> = Vec::new();

    let mut total_by_id: BTreeMap<String, usize> = BTreeMap::new();
    let mut placed_count_by_id: BTreeMap<String, usize> = BTreeMap::new();
    let mut spec_by_id: BTreeMap<String, InflatedPartSpec> = BTreeMap::new();
    for spec in parts {
        total_by_id.insert(spec.id.clone(), spec.quantity);
        placed_count_by_id.insert(spec.id.clone(), 0);
        spec_by_id.insert(spec.id.clone(), spec.clone());
    }

    loop {
        let mut remaining_specs: Vec<InflatedPartSpec> = Vec::new();
        for (id, total) in &total_by_id {
            let placed_cnt = *placed_count_by_id.get(id).unwrap_or(&0);
            let remaining = total.saturating_sub(placed_cnt);
            if remaining == 0 {
                continue;
            }
            if let Some(base) = spec_by_id.get(id) {
                remaining_specs.push(InflatedPartSpec {
                    id: id.clone(),
                    quantity: remaining,
                    allowed_rotations_deg: base.allowed_rotations_deg.clone(),
                    inflated_polygon: base.inflated_polygon.clone(),
                    nominal_bbox_area: base.nominal_bbox_area,
                });
            }
        }

        if remaining_specs.is_empty() {
            break;
        }
        if started_at.elapsed().as_secs() >= time_limit_sec {
            break;
        }

        let round: PlacementResult = match placer_kind {
            PlacerKind::Blf => blf_place(
                &remaining_specs,
                bin_polygon,
                grid_step_mm,
                time_limit_sec,
                started_at,
            ),
            PlacerKind::Nfp => nfp_place(
                &remaining_specs,
                bin_polygon,
                grid_step_mm,
                time_limit_sec,
                started_at,
                &mut nfp_cache,
            ),
        };

        let mut placed_this_round = 0usize;
        let mut local_count_by_id: BTreeMap<String, usize> = BTreeMap::new();
        for mut item in round.placed {
            let prev_total = *placed_count_by_id.get(&item.part_id).unwrap_or(&0);
            let local_seen = local_count_by_id.entry(item.part_id.clone()).or_insert(0);
            item.instance = prev_total + *local_seen;
            item.sheet = sheet_index;
            *local_seen += 1;
            placed_this_round += 1;
            placed.push(item);
        }
        for (id, c) in local_count_by_id {
            let cur = placed_count_by_id.entry(id).or_insert(0);
            *cur += c;
        }

        let round_timed_out = round
            .unplaced
            .iter()
            .any(|u| u.reason == "TIME_LIMIT_EXCEEDED");
        if round_timed_out || started_at.elapsed().as_secs() >= time_limit_sec {
            break;
        }
        if placed_this_round == 0 {
            break;
        }

        sheet_index += 1;
    }

    let mut unplaced: Vec<UnplacedItem> = Vec::new();
    let timed_out = started_at.elapsed().as_secs() >= time_limit_sec;
    for (id, total) in total_by_id {
        let placed_cnt = *placed_count_by_id.get(&id).unwrap_or(&0);
        for idx in placed_cnt..total {
            unplaced.push(UnplacedItem {
                part_id: id.clone(),
                instance: idx,
                reason: if timed_out {
                    "TIME_LIMIT_EXCEEDED".to_string()
                } else {
                    "PART_NEVER_FITS_SHEET".to_string()
                },
            });
        }
    }

    let sheets_used = if placed.is_empty() {
        0
    } else {
        placed.iter().map(|p| p.sheet).max().unwrap_or(0) + 1
    };
    MultiSheetResult {
        placed,
        unplaced,
        sheets_used,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::placement::blf::{InflatedPartSpec, bbox_area, rect_poly};

    #[test]
    fn basic_greedy_multi_sheet() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 4,
            allowed_rotations_deg: vec![0],
            inflated_polygon: rect_poly(9.0, 9.0),
            nominal_bbox_area: bbox_area(&rect_poly(9.0, 9.0).outer),
        };
        let bin = rect_poly(20.0, 20.0);
        let out = greedy_multi_sheet(&[part], &bin, 1.0, 30, PlacerKind::Blf);
        assert!(!out.placed.is_empty());
    }
}
