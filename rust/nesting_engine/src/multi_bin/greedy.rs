use std::collections::{BTreeMap, BTreeSet};
use std::time::Instant;

use crate::geometry::types::Polygon64;
use crate::placement::blf::{InflatedPartSpec, UnplacedItem};
use crate::placement::nfp_placer::NfpPlacerStatsV1;
use crate::placement::{PlacedItem, PlacementResult, blf_place, nfp_place};
use nesting_engine::nfp::cache::NfpCache;

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
}

pub fn greedy_multi_sheet(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    time_limit_sec: u64,
    placer_kind: PlacerKind,
    order_policy: PartOrderPolicy,
    part_in_part_mode: PartInPartMode,
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

    let sheets_used = if placed.is_empty() {
        0
    } else {
        placed.iter().map(|p| p.sheet).max().unwrap_or(0) + 1
    };
    let result = MultiSheetResult {
        placed,
        unplaced,
        sheets_used,
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
        let (out, stats) = greedy_multi_sheet(
            &[part],
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        assert!(stats.is_none());
        assert!(!out.placed.is_empty());
    }
}
