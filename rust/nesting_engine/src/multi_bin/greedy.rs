use std::collections::{BTreeMap, BTreeSet};
use std::time::Instant;

use crate::feasibility::{
    aabb::{Aabb, aabb_from_polygon64},
    can_place, PlacedPart,
    narrow::PlacedIndex,
};
use crate::geometry::scale::{i64_to_mm, mm_to_i64};
use crate::geometry::types::Polygon64;
use crate::placement::blf::{
    InflatedPartSpec, UnplacedItem, placed_extents_max_xy_i64, placed_polygon_for_state,
    rotated_inflated_aabb,
};
use crate::placement::nfp_placer::NfpPlacerStatsV1;
use crate::placement::{PlacedItem, PlacementResult, blf_place, nfp_place};
use nesting_engine::nfp::cache::NfpCache;

const SCORE_PPM_SCALE: u128 = 1_000_000;
const REMNANT_AREA_WEIGHT_PPM: u128 = 500_000;
const REMNANT_COMPACTNESS_WEIGHT_PPM: u128 = 300_000;
const REMNANT_MIN_WIDTH_WEIGHT_PPM: u128 = 200_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlacerKind {
    Blf,
    Nfp,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PartOrderPolicy {
    ByArea,
    ByInputOrder,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PartInPartMode {
    Off,
    Auto,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompactionMode {
    Off,
    Slide,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopMode {
    WallClock,
    WorkBudget,
}

#[derive(Debug, Clone)]
pub struct StopPolicy {
    mode: StopMode,
    started_at: Instant,
    time_limit_sec: u64,
    hard_timeout_grace_sec: u64,
    work_budget_remaining: Option<u64>,
    timed_out: bool,
}

impl StopPolicy {
    const DEFAULT_WORK_UNITS_PER_SEC: u64 = 50_000;
    const DEFAULT_HARD_TIMEOUT_GRACE_SEC: u64 = 60;

    pub fn from_env(time_limit_sec: u64, started_at: Instant) -> Self {
        let mode = match std::env::var("NESTING_ENGINE_STOP_MODE")
            .unwrap_or_else(|_| "wall_clock".to_string())
            .trim()
            .to_ascii_lowercase()
            .as_str()
        {
            "work_budget" => StopMode::WorkBudget,
            _ => StopMode::WallClock,
        };

        let hard_timeout_grace_sec = Self::read_env_u64(
            "NESTING_ENGINE_HARD_TIMEOUT_GRACE_SEC",
            Self::DEFAULT_HARD_TIMEOUT_GRACE_SEC,
        );

        let work_budget_remaining = if mode == StopMode::WorkBudget {
            let units_per_sec = Self::read_env_u64(
                "NESTING_ENGINE_WORK_UNITS_PER_SEC",
                Self::DEFAULT_WORK_UNITS_PER_SEC,
            )
            .max(1);
            Some(time_limit_sec.saturating_mul(units_per_sec).max(1))
        } else {
            None
        };

        Self {
            mode,
            started_at,
            time_limit_sec,
            hard_timeout_grace_sec,
            work_budget_remaining,
            timed_out: false,
        }
    }

    fn read_env_u64(key: &str, default: u64) -> u64 {
        std::env::var(key)
            .ok()
            .and_then(|raw| raw.trim().parse::<u64>().ok())
            .unwrap_or(default)
    }

    #[cfg(test)]
    pub(crate) fn wall_clock_for_test(time_limit_sec: u64, started_at: Instant) -> Self {
        Self {
            mode: StopMode::WallClock,
            started_at,
            time_limit_sec,
            hard_timeout_grace_sec: Self::DEFAULT_HARD_TIMEOUT_GRACE_SEC,
            work_budget_remaining: None,
            timed_out: false,
        }
    }

    #[cfg(test)]
    pub(crate) fn work_budget_for_test(
        time_limit_sec: u64,
        work_budget_units: u64,
        hard_timeout_grace_sec: u64,
        started_at: Instant,
    ) -> Self {
        Self {
            mode: StopMode::WorkBudget,
            started_at,
            time_limit_sec,
            hard_timeout_grace_sec,
            work_budget_remaining: Some(work_budget_units.max(1)),
            timed_out: false,
        }
    }

    pub fn consume(&mut self, units: u64) -> bool {
        if self.should_stop() {
            return true;
        }
        if self.mode != StopMode::WorkBudget {
            return false;
        }
        if units == 0 {
            return self.should_stop();
        }

        let remaining = self.work_budget_remaining.unwrap_or(0);
        if remaining <= units {
            self.work_budget_remaining = Some(0);
            self.timed_out = true;
            return true;
        }

        self.work_budget_remaining = Some(remaining - units);
        false
    }

    pub fn should_stop(&mut self) -> bool {
        let elapsed_sec = self.started_at.elapsed().as_secs();
        if self.mode == StopMode::WallClock && elapsed_sec >= self.time_limit_sec {
            self.timed_out = true;
            return true;
        }

        if self.mode == StopMode::WorkBudget {
            if self.work_budget_remaining.unwrap_or(0) == 0 {
                self.timed_out = true;
                return true;
            }
            let hard_deadline = self
                .time_limit_sec
                .saturating_add(self.hard_timeout_grace_sec);
            if elapsed_sec >= hard_deadline {
                self.timed_out = true;
                return true;
            }
        }
        false
    }

    pub fn mark_timed_out(&mut self) {
        self.timed_out = true;
    }

    pub fn is_timed_out(&self) -> bool {
        self.timed_out
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct MultiSheetResult {
    pub placed: Vec<PlacedItem>,
    pub unplaced: Vec<UnplacedItem>,
    pub sheets_used: usize,
    pub remnant_value_ppm: u64,
    pub remnant_area_score_ppm: u64,
    pub remnant_compactness_score_ppm: u64,
    pub remnant_min_width_score_ppm: u64,
    pub compaction: CompactionEvidence,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
struct RemnantObjectiveTotals {
    value_ppm: u64,
    area_score_ppm: u64,
    compactness_score_ppm: u64,
    min_width_score_ppm: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
struct RemnantSheetScore {
    value_ppm: u64,
    area_score_ppm: u64,
    compactness_score_ppm: u64,
    min_width_score_ppm: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct SheetEnvelopeExtents {
    max_x: i64,
    max_y: i64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OccupiedExtentI64 {
    pub min_x: i64,
    pub min_y: i64,
    pub max_x: i64,
    pub max_y: i64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CompactionEvidence {
    pub mode: CompactionMode,
    pub applied: bool,
    pub moved_items_count: u64,
    pub occupied_extent_before: Option<OccupiedExtentI64>,
    pub occupied_extent_after: Option<OccupiedExtentI64>,
}

#[derive(Debug, Clone)]
struct CompactionPlacedState {
    placed_index: usize,
    rotation_deg: i32,
    tx: i64,
    ty: i64,
    inflated_polygon: Polygon64,
    polygon: Polygon64,
    aabb: Aabb,
}

fn ppm_ratio(numerator: i128, denominator: i128) -> u64 {
    if denominator <= 0 {
        return 0;
    }
    let num = numerator.clamp(0, denominator) as u128;
    let den = denominator as u128;
    let raw = num.saturating_mul(SCORE_PPM_SCALE) / den;
    raw.min(SCORE_PPM_SCALE) as u64
}

fn compute_sheet_remnant_score(
    sheet_width: i128,
    sheet_height: i128,
    occupied_envelope_width: i128,
    occupied_envelope_height: i128,
) -> RemnantSheetScore {
    if sheet_width <= 0 || sheet_height <= 0 {
        return RemnantSheetScore::default();
    }
    let envelope_w = occupied_envelope_width.clamp(0, sheet_width);
    let envelope_h = occupied_envelope_height.clamp(0, sheet_height);

    let sheet_area = sheet_width.saturating_mul(sheet_height);
    let right_strip_width = sheet_width.saturating_sub(envelope_w);
    let top_strip_height = sheet_height.saturating_sub(envelope_h);
    let right_strip_area = right_strip_width.saturating_mul(sheet_height);
    let top_strip_area = envelope_w.saturating_mul(top_strip_height);
    let free_proxy_area = right_strip_area.saturating_add(top_strip_area);

    let area_score_ppm = ppm_ratio(free_proxy_area, sheet_area);
    let compactness_score_ppm = ppm_ratio(
        right_strip_area.max(top_strip_area),
        free_proxy_area.max(1),
    );
    let min_width_score_ppm = ppm_ratio(
        right_strip_width.max(top_strip_height),
        sheet_width.min(sheet_height).max(1),
    );

    let weighted_value = REMNANT_AREA_WEIGHT_PPM
        .saturating_mul(area_score_ppm as u128)
        .saturating_add(REMNANT_COMPACTNESS_WEIGHT_PPM.saturating_mul(compactness_score_ppm as u128))
        .saturating_add(REMNANT_MIN_WIDTH_WEIGHT_PPM.saturating_mul(min_width_score_ppm as u128))
        / SCORE_PPM_SCALE;

    let value_ppm = weighted_value.min(SCORE_PPM_SCALE) as u64;
    RemnantSheetScore {
        value_ppm,
        area_score_ppm,
        compactness_score_ppm,
        min_width_score_ppm,
    }
}

fn compute_remnant_proxy_totals(
    placed: &[PlacedItem],
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
) -> RemnantObjectiveTotals {
    if placed.is_empty() {
        return RemnantObjectiveTotals::default();
    }

    let sheet_bbox = aabb_from_polygon64(bin_polygon);
    let sheet_width = (sheet_bbox.max_x as i128).saturating_sub(sheet_bbox.min_x as i128);
    let sheet_height = (sheet_bbox.max_y as i128).saturating_sub(sheet_bbox.min_y as i128);
    if sheet_width <= 0 || sheet_height <= 0 {
        return RemnantObjectiveTotals::default();
    }

    let mut part_by_id: BTreeMap<&str, &InflatedPartSpec> = BTreeMap::new();
    for spec in parts {
        part_by_id.insert(spec.id.as_str(), spec);
    }

    let mut per_rotation_max_cache: BTreeMap<(String, i32), (i64, i64)> = BTreeMap::new();
    let mut envelope_by_sheet: BTreeMap<usize, SheetEnvelopeExtents> = BTreeMap::new();

    for item in placed {
        let tx = mm_to_i64(item.x_mm);
        let ty = mm_to_i64(item.y_mm);

        let entry = envelope_by_sheet
            .entry(item.sheet)
            .or_insert(SheetEnvelopeExtents {
                max_x: sheet_bbox.min_x,
                max_y: sheet_bbox.min_y,
            });

        let cache_key = (item.part_id.clone(), item.rotation_deg);
        let (rot_max_x, rot_max_y) = if let Some(v) = per_rotation_max_cache.get(&cache_key) {
            *v
        } else if let Some(spec) = part_by_id.get(item.part_id.as_str()) {
            let max_xy =
                placed_extents_max_xy_i64(&spec.inflated_polygon, item.rotation_deg, 0, 0);
            per_rotation_max_cache.insert(cache_key, max_xy);
            max_xy
        } else {
            (0, 0)
        };

        let occupied_max_x = tx.saturating_add(rot_max_x);
        let occupied_max_y = ty.saturating_add(rot_max_y);
        entry.max_x = entry.max_x.max(occupied_max_x);
        entry.max_y = entry.max_y.max(occupied_max_y);
    }

    let mut totals = RemnantObjectiveTotals::default();
    for extents in envelope_by_sheet.values() {
        let envelope_w =
            (extents.max_x as i128).saturating_sub(sheet_bbox.min_x as i128).clamp(0, sheet_width);
        let envelope_h =
            (extents.max_y as i128).saturating_sub(sheet_bbox.min_y as i128).clamp(0, sheet_height);
        let score = compute_sheet_remnant_score(sheet_width, sheet_height, envelope_w, envelope_h);
        totals.value_ppm = totals.value_ppm.saturating_add(score.value_ppm);
        totals.area_score_ppm = totals.area_score_ppm.saturating_add(score.area_score_ppm);
        totals.compactness_score_ppm = totals
            .compactness_score_ppm
            .saturating_add(score.compactness_score_ppm);
        totals.min_width_score_ppm = totals
            .min_width_score_ppm
            .saturating_add(score.min_width_score_ppm);
    }

    totals
}

fn compute_occupied_extent_i64(
    placed: &[PlacedItem],
    parts: &[InflatedPartSpec],
) -> Option<OccupiedExtentI64> {
    if placed.is_empty() {
        return None;
    }

    let mut part_by_id: BTreeMap<&str, &InflatedPartSpec> = BTreeMap::new();
    for spec in parts {
        part_by_id.insert(spec.id.as_str(), spec);
    }

    let mut out: Option<OccupiedExtentI64> = None;
    for item in placed {
        let Some(spec) = part_by_id.get(item.part_id.as_str()) else {
            continue;
        };
        let tx = mm_to_i64(item.x_mm);
        let ty = mm_to_i64(item.y_mm);
        let rotated_aabb = rotated_inflated_aabb(&spec.inflated_polygon, item.rotation_deg);
        let min_x = tx.saturating_add(rotated_aabb.min_x);
        let min_y = ty.saturating_add(rotated_aabb.min_y);
        let max_x = tx.saturating_add(rotated_aabb.max_x);
        let max_y = ty.saturating_add(rotated_aabb.max_y);

        out = Some(match out {
            None => OccupiedExtentI64 {
                min_x,
                min_y,
                max_x,
                max_y,
            },
            Some(prev) => OccupiedExtentI64 {
                min_x: prev.min_x.min(min_x),
                min_y: prev.min_y.min(min_y),
                max_x: prev.max_x.max(max_x),
                max_y: prev.max_y.max(max_y),
            },
        });
    }

    out
}

fn collect_candidate_left_positions(
    item_idx: usize,
    states: &[CompactionPlacedState],
    rotated_aabb: Aabb,
    tx_min: i64,
) -> Vec<i64> {
    let current = &states[item_idx];
    let mut candidates: BTreeSet<i64> = BTreeSet::new();
    candidates.insert(tx_min);
    candidates.insert(current.tx);

    for (other_idx, other) in states.iter().enumerate() {
        if other_idx == item_idx {
            continue;
        }
        let anchor_touch = other.aabb.max_x.saturating_sub(rotated_aabb.min_x);
        let anchor_gap = anchor_touch.saturating_add(1);
        if anchor_touch <= current.tx {
            candidates.insert(anchor_touch);
        }
        if anchor_gap <= current.tx {
            candidates.insert(anchor_gap);
        }
    }

    candidates.into_iter().collect()
}

fn collect_candidate_down_positions(
    item_idx: usize,
    states: &[CompactionPlacedState],
    rotated_aabb: Aabb,
    ty_min: i64,
) -> Vec<i64> {
    let current = &states[item_idx];
    let mut candidates: BTreeSet<i64> = BTreeSet::new();
    candidates.insert(ty_min);
    candidates.insert(current.ty);

    for (other_idx, other) in states.iter().enumerate() {
        if other_idx == item_idx {
            continue;
        }
        let anchor_touch = other.aabb.max_y.saturating_sub(rotated_aabb.min_y);
        let anchor_gap = anchor_touch.saturating_add(1);
        if anchor_touch <= current.ty {
            candidates.insert(anchor_touch);
        }
        if anchor_gap <= current.ty {
            candidates.insert(anchor_gap);
        }
    }

    candidates.into_iter().collect()
}

fn can_place_with_current_sheet_state(
    item_idx: usize,
    candidate_polygon: &Polygon64,
    states: &[CompactionPlacedState],
    bin_polygon: &Polygon64,
) -> bool {
    let mut placed_index = PlacedIndex::new();
    for (other_idx, state) in states.iter().enumerate() {
        if other_idx == item_idx {
            continue;
        }
        placed_index.insert(PlacedPart {
            inflated_polygon: state.polygon.clone(),
            aabb: state.aabb,
        });
    }
    can_place(candidate_polygon, bin_polygon, &placed_index)
}

fn run_slide_compaction_postpass(
    placed: &mut [PlacedItem],
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
) -> u64 {
    if placed.is_empty() {
        return 0;
    }

    let mut part_by_id: BTreeMap<&str, &InflatedPartSpec> = BTreeMap::new();
    for spec in parts {
        part_by_id.insert(spec.id.as_str(), spec);
    }

    let mut sheet_to_indices: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for (idx, item) in placed.iter().enumerate() {
        sheet_to_indices.entry(item.sheet).or_default().push(idx);
    }

    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut moved_items_count = 0_u64;

    for placed_indices in sheet_to_indices.values() {
        let mut states: Vec<CompactionPlacedState> = Vec::new();
        for &placed_index in placed_indices {
            let item = &placed[placed_index];
            let Some(spec) = part_by_id.get(item.part_id.as_str()) else {
                continue;
            };
            let tx = mm_to_i64(item.x_mm);
            let ty = mm_to_i64(item.y_mm);
            let polygon = placed_polygon_for_state(&spec.inflated_polygon, item.rotation_deg, tx, ty);
            states.push(CompactionPlacedState {
                placed_index,
                rotation_deg: item.rotation_deg,
                tx,
                ty,
                inflated_polygon: spec.inflated_polygon.clone(),
                aabb: aabb_from_polygon64(&polygon),
                polygon,
            });
        }

        for item_idx in 0..states.len() {
            let mut moved_this_item = false;
            loop {
                let rotated_aabb = rotated_inflated_aabb(
                    &states[item_idx].inflated_polygon,
                    states[item_idx].rotation_deg,
                );
                let tx_min = bin_aabb.min_x.saturating_sub(rotated_aabb.min_x);
                let ty_min = bin_aabb.min_y.saturating_sub(rotated_aabb.min_y);
                let mut changed = false;

                for candidate_tx in collect_candidate_left_positions(
                    item_idx,
                    &states,
                    rotated_aabb,
                    tx_min,
                ) {
                    if candidate_tx >= states[item_idx].tx {
                        continue;
                    }
                    let candidate_polygon = placed_polygon_for_state(
                        &states[item_idx].inflated_polygon,
                        states[item_idx].rotation_deg,
                        candidate_tx,
                        states[item_idx].ty,
                    );
                    if can_place_with_current_sheet_state(
                        item_idx,
                        &candidate_polygon,
                        &states,
                        bin_polygon,
                    ) {
                        states[item_idx].tx = candidate_tx;
                        states[item_idx].polygon = candidate_polygon;
                        states[item_idx].aabb = aabb_from_polygon64(&states[item_idx].polygon);
                        moved_this_item = true;
                        changed = true;
                        break;
                    }
                }

                for candidate_ty in collect_candidate_down_positions(
                    item_idx,
                    &states,
                    rotated_aabb,
                    ty_min,
                ) {
                    if candidate_ty >= states[item_idx].ty {
                        continue;
                    }
                    let candidate_polygon = placed_polygon_for_state(
                        &states[item_idx].inflated_polygon,
                        states[item_idx].rotation_deg,
                        states[item_idx].tx,
                        candidate_ty,
                    );
                    if can_place_with_current_sheet_state(
                        item_idx,
                        &candidate_polygon,
                        &states,
                        bin_polygon,
                    ) {
                        states[item_idx].ty = candidate_ty;
                        states[item_idx].polygon = candidate_polygon;
                        states[item_idx].aabb = aabb_from_polygon64(&states[item_idx].polygon);
                        moved_this_item = true;
                        changed = true;
                        break;
                    }
                }

                if !changed {
                    break;
                }
            }

            if moved_this_item {
                moved_items_count = moved_items_count.saturating_add(1);
            }
        }

        for state in &states {
            placed[state.placed_index].x_mm = i64_to_mm(state.tx);
            placed[state.placed_index].y_mm = i64_to_mm(state.ty);
        }
    }

    moved_items_count
}

pub fn greedy_multi_sheet(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    time_limit_sec: u64,
    placer_kind: PlacerKind,
    order_policy: PartOrderPolicy,
    part_in_part_mode: PartInPartMode,
    compaction_mode: CompactionMode,
) -> (MultiSheetResult, Option<NfpPlacerStatsV1>) {
    let started_at = Instant::now();
    let mut stop = StopPolicy::from_env(time_limit_sec, started_at);
    let mut nfp_cache = NfpCache::new();
    let mut nfp_stats_total = if placer_kind == PlacerKind::Nfp {
        Some(NfpPlacerStatsV1::default())
    } else {
        None
    };
    let mut sheet_index = 0usize;
    let mut placed: Vec<PlacedItem> = Vec::new();

    let mut total_by_id: BTreeMap<String, usize> = BTreeMap::new();
    let mut placed_count_by_id: BTreeMap<String, usize> = BTreeMap::new();
    let mut spec_by_id: BTreeMap<String, InflatedPartSpec> = BTreeMap::new();
    let mut input_order_ids: Vec<String> = Vec::new();
    let mut seen_ids: BTreeSet<String> = BTreeSet::new();
    for spec in parts {
        total_by_id.insert(spec.id.clone(), spec.quantity);
        placed_count_by_id.insert(spec.id.clone(), 0);
        spec_by_id.insert(spec.id.clone(), spec.clone());
        if seen_ids.insert(spec.id.clone()) {
            input_order_ids.push(spec.id.clone());
        }
    }

    loop {
        let mut remaining_specs: Vec<InflatedPartSpec> = Vec::new();
        match order_policy {
            PartOrderPolicy::ByArea => {
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
            }
            PartOrderPolicy::ByInputOrder => {
                for id in &input_order_ids {
                    let Some(total) = total_by_id.get(id) else {
                        continue;
                    };
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
            }
        }

        if remaining_specs.is_empty() {
            break;
        }
        if stop.should_stop() {
            break;
        }

        let round: PlacementResult = match placer_kind {
            PlacerKind::Blf => blf_place(
                &remaining_specs,
                bin_polygon,
                grid_step_mm,
                &mut stop,
                order_policy,
                part_in_part_mode,
            ),
            PlacerKind::Nfp => {
                let mut round_stats = NfpPlacerStatsV1::default();
                let round = nfp_place(
                    &remaining_specs,
                    bin_polygon,
                    grid_step_mm,
                    &mut stop,
                    &mut nfp_cache,
                    &mut round_stats,
                    order_policy,
                );
                if let Some(total) = nfp_stats_total.as_mut() {
                    total.add_assign(&round_stats);
                }
                round
            }
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
        if round_timed_out {
            stop.mark_timed_out();
        }
        if round_timed_out || stop.should_stop() {
            break;
        }
        if placed_this_round == 0 {
            break;
        }

        sheet_index += 1;
    }

    let mut unplaced: Vec<UnplacedItem> = Vec::new();
    let timed_out = stop.is_timed_out() || started_at.elapsed().as_secs() >= time_limit_sec;
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

    let occupied_extent_before = compute_occupied_extent_i64(&placed, parts);
    let compaction_moved_items_count = if compaction_mode == CompactionMode::Slide {
        run_slide_compaction_postpass(&mut placed, parts, bin_polygon)
    } else {
        0
    };
    let occupied_extent_after = compute_occupied_extent_i64(&placed, parts);

    let sheets_used = if placed.is_empty() {
        0
    } else {
        placed.iter().map(|p| p.sheet).max().unwrap_or(0) + 1
    };
    let remnant = compute_remnant_proxy_totals(&placed, parts, bin_polygon);
    let result = MultiSheetResult {
        placed,
        unplaced,
        sheets_used,
        remnant_value_ppm: remnant.value_ppm,
        remnant_area_score_ppm: remnant.area_score_ppm,
        remnant_compactness_score_ppm: remnant.compactness_score_ppm,
        remnant_min_width_score_ppm: remnant.min_width_score_ppm,
        compaction: CompactionEvidence {
            mode: compaction_mode,
            applied: compaction_moved_items_count > 0,
            moved_items_count: compaction_moved_items_count,
            occupied_extent_before,
            occupied_extent_after,
        },
    };

    if let Some(stats) = nfp_stats_total.as_mut() {
        stats.nfp_cache_entries_end = nfp_cache.stats().entries as u64;
        stats.effective_placer = "nfp".to_string();
        stats.sheets_used = result.sheets_used as u64;
    }

    (result, nfp_stats_total)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::placement::blf::{InflatedPartSpec, PlacedItem, bbox_area, rect_poly};

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
        let (out, stats) = greedy_multi_sheet(
            &[part],
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        assert!(stats.is_none());
        assert!(!out.placed.is_empty());
        assert!(out.remnant_value_ppm > 0);
        assert!(out.remnant_area_score_ppm > 0);
    }

    #[test]
    fn remnant_score_prefers_more_compact_proxy_layout() {
        let bin = rect_poly(100.0, 100.0);
        let compact_poly = rect_poly(100.0, 60.0);
        let split_poly = rect_poly(80.0, 75.0);
        let parts = vec![
            InflatedPartSpec {
                id: "compact".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: compact_poly.clone(),
                nominal_bbox_area: bbox_area(&compact_poly.outer),
            },
            InflatedPartSpec {
                id: "split".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: split_poly.clone(),
                nominal_bbox_area: bbox_area(&split_poly.outer),
            },
        ];

        let compact_layout = vec![PlacedItem {
            part_id: "compact".to_string(),
            instance: 0,
            sheet: 0,
            x_mm: 0.0,
            y_mm: 0.0,
            rotation_deg: 0,
        }];
        let split_layout = vec![PlacedItem {
            part_id: "split".to_string(),
            instance: 0,
            sheet: 0,
            x_mm: 0.0,
            y_mm: 0.0,
            rotation_deg: 0,
        }];

        let compact_score = compute_remnant_proxy_totals(&compact_layout, &parts, &bin);
        let split_score = compute_remnant_proxy_totals(&split_layout, &parts, &bin);

        assert_eq!(compact_score.area_score_ppm, split_score.area_score_ppm);
        assert!(compact_score.compactness_score_ppm > split_score.compactness_score_ppm);
        assert!(compact_score.value_ppm > split_score.value_ppm);
    }

    #[test]
    fn remnant_score_is_integer_and_deterministic() {
        let bin = rect_poly(100.0, 100.0);
        let part_poly = rect_poly(60.0, 35.0);
        let parts = vec![InflatedPartSpec {
            id: "p".to_string(),
            quantity: 1,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: part_poly.clone(),
            nominal_bbox_area: bbox_area(&part_poly.outer),
        }];
        let layout = vec![PlacedItem {
            part_id: "p".to_string(),
            instance: 0,
            sheet: 0,
            x_mm: 7.0,
            y_mm: 3.0,
            rotation_deg: 90,
        }];

        let score_a = compute_remnant_proxy_totals(&layout, &parts, &bin);
        let score_b = compute_remnant_proxy_totals(&layout, &parts, &bin);

        assert_eq!(score_a, score_b);
        assert!(score_a.value_ppm <= 1_000_000);
        assert!(score_a.area_score_ppm <= 1_000_000);
        assert!(score_a.compactness_score_ppm <= 1_000_000);
        assert!(score_a.min_width_score_ppm <= 1_000_000);
    }

    fn compaction_slide_fixture_parts() -> Vec<InflatedPartSpec> {
        let small = rect_poly(10.2, 10.0);
        vec![
            InflatedPartSpec {
                id: "a".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: small.clone(),
                nominal_bbox_area: bbox_area(&small.outer),
            },
            InflatedPartSpec {
                id: "b".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: small.clone(),
                nominal_bbox_area: bbox_area(&small.outer),
            },
            InflatedPartSpec {
                id: "c".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: small,
                nominal_bbox_area: bbox_area(&rect_poly(10.2, 10.0).outer),
            },
        ]
    }

    #[test]
    fn compaction_postpass_primary_objective_is_not_worse() {
        let parts = compaction_slide_fixture_parts();
        let bin = rect_poly(40.0, 20.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        let (slide_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Slide,
        );

        assert_eq!(slide_result.unplaced.len(), off_result.unplaced.len());
        assert_eq!(slide_result.sheets_used, off_result.sheets_used);
    }

    #[test]
    fn compaction_postpass_is_deterministic_for_identical_input() {
        let parts = compaction_slide_fixture_parts();
        let bin = rect_poly(40.0, 20.0);

        let (run_a, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Slide,
        );
        let (run_b, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Slide,
        );
        assert_eq!(run_a, run_b);
    }

    #[test]
    fn compaction_slide_fixture_improves_extent_or_remnant() {
        let parts = compaction_slide_fixture_parts();
        let bin = rect_poly(40.0, 20.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        let (slide_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Slide,
        );

        assert!(slide_result.compaction.applied);
        assert!(slide_result.compaction.moved_items_count > 0);

        let off_after = off_result.compaction.occupied_extent_after.expect("off extent");
        let slide_after = slide_result
            .compaction
            .occupied_extent_after
            .expect("slide extent");

        let off_w = off_after.max_x.saturating_sub(off_after.min_x);
        let off_h = off_after.max_y.saturating_sub(off_after.min_y);
        let slide_w = slide_after.max_x.saturating_sub(slide_after.min_x);
        let slide_h = slide_after.max_y.saturating_sub(slide_after.min_y);

        let extent_not_worse = slide_w <= off_w && slide_h <= off_h;
        let remnant_not_worse = slide_result.remnant_value_ppm >= off_result.remnant_value_ppm;
        assert!(extent_not_worse || remnant_not_worse);
    }
}
