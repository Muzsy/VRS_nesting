use std::sync::Once;

use crate::{
    geometry::types::Polygon64,
    multi_bin::{
        greedy::{PartOrderPolicy, PlacerKind},
        greedy_multi_sheet, MultiSheetResult,
    },
    placement::{blf::InflatedPartSpec, nfp_placer::NfpPlacerStatsV1},
};

static SA_WORK_BUDGET_NOTICE: Once = Once::new();

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SaConfig {
    pub iters: u64,
    pub temp_start: u64,
    pub temp_end: u64,
    pub seed: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SaSearchConfig {
    pub iters: u64,
    pub temp_start: u64,
    pub temp_end: u64,
    pub seed: u64,
    pub eval_budget_sec: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SaState {
    pub order: Vec<usize>,
    pub rot_choice: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SaRunResult {
    pub best_state: SaState,
    pub best_cost: i64,
    pub final_state: SaState,
    pub final_cost: i64,
}

#[derive(Debug, Clone)]
pub struct SplitMix64 {
    state: u64,
}

#[derive(Debug, Clone, Copy)]
struct CostEncoding {
    unplaced_weight: u128,
    sheets_weight: u128,
}

impl SplitMix64 {
    pub fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

pub fn run_sa_core<F>(
    initial_state: SaState,
    rotation_options_len: &[u8],
    config: SaConfig,
    mut evaluate: F,
) -> Result<SaRunResult, String>
where
    F: FnMut(&SaState) -> i64,
{
    validate_state(&initial_state, rotation_options_len)?;

    let mut rng = SplitMix64::new(config.seed);
    let mut current_state = initial_state.clone();
    let mut current_cost = evaluate(&current_state);
    let mut best_state = current_state.clone();
    let mut best_cost = current_cost;

    for iter in 0..config.iters {
        let mut candidate = current_state.clone();
        apply_neighbor(&mut candidate, rotation_options_len, &mut rng);

        let candidate_cost = evaluate(&candidate);
        let delta = (candidate_cost as i128) - (current_cost as i128);
        let temp = linear_temp(config.temp_start, config.temp_end, config.iters, iter);

        let accept = if delta <= 0 {
            true
        } else {
            accept_worse(delta as u128, temp, &mut rng)
        };

        if accept {
            current_state = candidate;
            current_cost = candidate_cost;
        }

        if current_cost < best_cost
            || (current_cost == best_cost
                && lexicographically_precedes(&current_state, &best_state))
        {
            best_state = current_state.clone();
            best_cost = current_cost;
        }
    }

    Ok(SaRunResult {
        best_state,
        best_cost,
        final_state: current_state,
        final_cost: current_cost,
    })
}

pub fn run_sa_search_over_specs(
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    grid_step_mm: f64,
    placer_kind: PlacerKind,
    config: SaSearchConfig,
) -> Result<(MultiSheetResult, Option<NfpPlacerStatsV1>), String> {
    if config.eval_budget_sec == 0 {
        return Err("sa eval budget must be >= 1 second".to_string());
    }

    ensure_sa_stop_mode();

    if base_specs.is_empty() {
        return Ok(greedy_multi_sheet(
            base_specs,
            bin,
            grid_step_mm,
            config.eval_budget_sec,
            placer_kind,
            PartOrderPolicy::ByInputOrder,
        ));
    }

    let rotation_options_len = rotation_options_len(base_specs)?;
    let total_instances = total_instances(base_specs)?;
    let cost_encoding = CostEncoding::new(total_instances)?;

    let initial_state = SaState {
        order: (0..base_specs.len()).collect(),
        rot_choice: vec![0; base_specs.len()],
    };
    let core_cfg = SaConfig {
        iters: config.iters,
        temp_start: config.temp_start,
        temp_end: config.temp_end,
        seed: config.seed,
    };

    let mut eval_error: Option<String> = None;
    let run =
        run_sa_core(
            initial_state,
            &rotation_options_len,
            core_cfg,
            |state| match eval_state_cost(
                state,
                base_specs,
                bin,
                grid_step_mm,
                placer_kind,
                config.eval_budget_sec,
                total_instances,
                cost_encoding,
            ) {
                Ok(cost) => cost,
                Err(err) => {
                    if eval_error.is_none() {
                        eval_error = Some(err);
                    }
                    i64::MAX
                }
            },
        )?;
    if let Some(err) = eval_error {
        return Err(err);
    }

    let best_specs = specs_for_state(base_specs, &run.best_state);
    Ok(greedy_multi_sheet(
        &best_specs,
        bin,
        grid_step_mm,
        config.eval_budget_sec,
        placer_kind,
        PartOrderPolicy::ByInputOrder,
    ))
}

fn ensure_sa_stop_mode() {
    if std::env::var_os("NESTING_ENGINE_STOP_MODE").is_some() {
        return;
    }

    SA_WORK_BUDGET_NOTICE.call_once(|| {
        if std::env::var_os("NESTING_ENGINE_STOP_MODE").is_none() {
            std::env::set_var("NESTING_ENGINE_STOP_MODE", "work_budget");
            eprintln!("SA: forcing work_budget stop mode");
        }
    });
}

fn total_instances(base_specs: &[InflatedPartSpec]) -> Result<u64, String> {
    let mut total = 0_u64;
    for spec in base_specs {
        let qty = u64::try_from(spec.quantity)
            .map_err(|_| "part quantity does not fit into u64".to_string())?;
        total = total
            .checked_add(qty)
            .ok_or_else(|| "total part instance count overflow".to_string())?;
    }
    Ok(total)
}

impl CostEncoding {
    fn new(total_instances: u64) -> Result<Self, String> {
        let axis = u128::from(total_instances).saturating_add(1);
        let sheets_weight = axis;
        let unplaced_weight = axis
            .checked_mul(axis)
            .ok_or_else(|| "sa cost encoding overflow while computing weights".to_string())?;

        let max_total = u128::from(total_instances);
        let max_cost = max_total
            .checked_mul(unplaced_weight)
            .and_then(|v| v.checked_add(max_total.checked_mul(sheets_weight)?))
            .and_then(|v| v.checked_add(max_total))
            .ok_or_else(|| "sa cost encoding overflow while computing max cost".to_string())?;
        if max_cost > i64::MAX as u128 {
            return Err("sa cost encoding exceeds i64 range for this input size".to_string());
        }

        Ok(Self {
            unplaced_weight,
            sheets_weight,
        })
    }

    fn encode(self, unplaced_count: u64, sheets_used: u64, not_placed: u64) -> Result<i64, String> {
        let cost = u128::from(unplaced_count)
            .checked_mul(self.unplaced_weight)
            .and_then(|v| v.checked_add(u128::from(sheets_used).checked_mul(self.sheets_weight)?))
            .and_then(|v| v.checked_add(u128::from(not_placed)))
            .ok_or_else(|| "sa cost encoding overflow during evaluation".to_string())?;

        i64::try_from(cost).map_err(|_| "sa cost value does not fit into i64".to_string())
    }
}

fn eval_state_cost(
    state: &SaState,
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    grid_step_mm: f64,
    placer_kind: PlacerKind,
    eval_budget_sec: u64,
    total_instances: u64,
    cost_encoding: CostEncoding,
) -> Result<i64, String> {
    let specs = specs_for_state(base_specs, state);
    let (result, _stats) = greedy_multi_sheet(
        &specs,
        bin,
        grid_step_mm,
        eval_budget_sec,
        placer_kind,
        PartOrderPolicy::ByInputOrder,
    );

    let placed_count = u64::try_from(result.placed.len())
        .map_err(|_| "placed item count does not fit into u64".to_string())?;
    let unplaced_count = u64::try_from(result.unplaced.len())
        .map_err(|_| "unplaced item count does not fit into u64".to_string())?;
    let sheets_used = u64::try_from(result.sheets_used)
        .map_err(|_| "sheet count does not fit into u64".to_string())?;
    let not_placed = total_instances.saturating_sub(placed_count);

    cost_encoding.encode(unplaced_count, sheets_used, not_placed)
}

fn rotation_options_len(base_specs: &[InflatedPartSpec]) -> Result<Vec<u8>, String> {
    let mut out = Vec::with_capacity(base_specs.len());
    for spec in base_specs {
        let unique_count = unique_rotation_count(&spec.allowed_rotations_deg);
        let normalized = if unique_count == 0 { 1 } else { unique_count };
        let as_u8 = u8::try_from(normalized)
            .map_err(|_| "too many rotation options for SA state (max 255)".to_string())?;
        out.push(as_u8);
    }
    Ok(out)
}

fn unique_rotation_count(values: &[i32]) -> usize {
    if values.is_empty() {
        return 0;
    }
    let mut deduped = values.to_vec();
    deduped.sort_unstable();
    deduped.dedup();
    deduped.len()
}

fn specs_for_state(base_specs: &[InflatedPartSpec], state: &SaState) -> Vec<InflatedPartSpec> {
    let mut out = Vec::with_capacity(base_specs.len());
    for &spec_idx in &state.order {
        let mut spec = base_specs[spec_idx].clone();
        let rot_offset = usize::from(state.rot_choice[spec_idx]);
        spec.allowed_rotations_deg = rotate_slice(&spec.allowed_rotations_deg, rot_offset);
        out.push(spec);
    }
    out
}

fn rotate_slice(values: &[i32], offset: usize) -> Vec<i32> {
    if values.len() <= 1 {
        return values.to_vec();
    }
    let shift = offset % values.len();
    if shift == 0 {
        return values.to_vec();
    }

    let mut rotated = Vec::with_capacity(values.len());
    rotated.extend_from_slice(&values[shift..]);
    rotated.extend_from_slice(&values[..shift]);
    rotated
}

fn validate_state(state: &SaState, rotation_options_len: &[u8]) -> Result<(), String> {
    let n = state.order.len();
    if state.rot_choice.len() != n {
        return Err("state.rot_choice len must equal state.order len".to_string());
    }
    if rotation_options_len.len() != n {
        return Err("rotation_options_len len must equal state len".to_string());
    }

    let mut seen = vec![false; n];
    for &idx in &state.order {
        if idx >= n {
            return Err("state.order contains out-of-range index".to_string());
        }
        if seen[idx] {
            return Err("state.order must be a permutation without duplicates".to_string());
        }
        seen[idx] = true;
    }

    for (i, &choice) in state.rot_choice.iter().enumerate() {
        let opts = rotation_options_len[i];
        if opts == 0 {
            return Err("rotation_options_len values must be >= 1".to_string());
        }
        if choice >= opts {
            return Err("state.rot_choice entry out of range".to_string());
        }
    }

    Ok(())
}

fn apply_neighbor(state: &mut SaState, rotation_options_len: &[u8], rng: &mut SplitMix64) {
    let n = state.order.len();
    if n == 0 {
        return;
    }

    let can_swap = n >= 2;
    let can_rotate = rotation_options_len.iter().any(|&len| len > 1);

    if !can_swap && !can_rotate {
        return;
    }

    let prefer_swap = (rng.next_u64() & 1) == 0;
    if prefer_swap {
        if can_swap {
            apply_swap(state, rng);
        } else {
            apply_rotate(state, rotation_options_len, rng);
        }
    } else if can_rotate {
        apply_rotate(state, rotation_options_len, rng);
    } else {
        apply_swap(state, rng);
    }
}

fn apply_swap(state: &mut SaState, rng: &mut SplitMix64) {
    let n = state.order.len();
    if n < 2 {
        return;
    }

    let i = random_index(rng, n);
    let mut j = random_index(rng, n - 1);
    if j >= i {
        j += 1;
    }
    state.order.swap(i, j);
}

fn apply_rotate(state: &mut SaState, rotation_options_len: &[u8], rng: &mut SplitMix64) {
    let n = state.rot_choice.len();
    if n == 0 {
        return;
    }

    let start = random_index(rng, n);
    if let Some(k) = first_rotatable_from(start, rotation_options_len) {
        let len = rotation_options_len[k];
        state.rot_choice[k] = state.rot_choice[k].wrapping_add(1) % len;
    }
}

fn first_rotatable_from(start: usize, rotation_options_len: &[u8]) -> Option<usize> {
    let n = rotation_options_len.len();
    for step in 0..n {
        let idx = (start + step) % n;
        if rotation_options_len[idx] > 1 {
            return Some(idx);
        }
    }
    None
}

fn random_index(rng: &mut SplitMix64, len: usize) -> usize {
    (rng.next_u64() as usize) % len
}

fn linear_temp(temp_start: u64, temp_end: u64, iters: u64, iter: u64) -> u64 {
    if iters <= 1 {
        return temp_start;
    }

    let start = temp_start as i128;
    let end = temp_end as i128;
    let span = (iters - 1) as i128;
    let pos = iter as i128;
    let value = start + ((end - start) * pos) / span;
    if value <= 0 {
        0
    } else {
        value as u64
    }
}

fn accept_worse(delta: u128, temp: u64, rng: &mut SplitMix64) -> bool {
    let num = temp as u128;
    if num == 0 {
        return false;
    }
    let denom = num.saturating_add(delta);
    if denom == 0 {
        return false;
    }
    (rng.next_u64() as u128) % denom < num
}

fn lexicographically_precedes(a: &SaState, b: &SaState) -> bool {
    if a.order != b.order {
        return a.order < b.order;
    }
    a.rot_choice < b.rot_choice
}

#[cfg(test)]
mod tests {
    use super::{run_sa_core, run_sa_search_over_specs, SaConfig, SaSearchConfig, SaState};
    use crate::{
        multi_bin::{greedy::PartOrderPolicy, greedy::PlacerKind, greedy_multi_sheet},
        placement::blf::{bbox_area, rect_poly, InflatedPartSpec},
    };

    fn eval_cost(state: &SaState) -> i64 {
        let mut inversions = 0_i64;
        for i in 0..state.order.len() {
            for j in (i + 1)..state.order.len() {
                if state.order[i] > state.order[j] {
                    inversions += 1;
                }
            }
        }

        let position_penalty: i64 = state
            .order
            .iter()
            .enumerate()
            .map(|(pos, &id)| (id as i64 - pos as i64).abs())
            .sum();

        let rotation_penalty: i64 = state
            .rot_choice
            .iter()
            .enumerate()
            .map(|(idx, &rot)| (idx as i64 + 1) * rot as i64)
            .sum();

        inversions * 31 + position_penalty * 11 + rotation_penalty * 7
    }

    #[test]
    fn sa_core_is_deterministic_fixed_seed() {
        let initial = SaState {
            order: vec![0, 1, 2, 3, 4, 5, 6, 7],
            rot_choice: vec![0, 0, 0, 0, 0, 0, 0, 0],
        };
        let rotation_options_len = vec![1, 2, 1, 3, 2, 1, 2, 3];
        let config = SaConfig {
            iters: 256,
            temp_start: 10_000,
            temp_end: 50,
            seed: 123_456,
        };

        let run_a = run_sa_core(initial.clone(), &rotation_options_len, config, eval_cost)
            .expect("run_a must succeed");
        let run_b = run_sa_core(initial, &rotation_options_len, config, eval_cost)
            .expect("run_b must succeed");

        assert_eq!(run_a.best_cost, run_b.best_cost);
        assert_eq!(run_a.best_state, run_b.best_state);
        assert_eq!(run_a.final_cost, run_b.final_cost);
        assert_eq!(run_a.final_state, run_b.final_state);
    }

    fn tiny_part(
        id: &str,
        w_mm: f64,
        h_mm: f64,
        allowed_rotations_deg: Vec<i32>,
    ) -> InflatedPartSpec {
        let poly = rect_poly(w_mm, h_mm);
        InflatedPartSpec {
            id: id.to_string(),
            quantity: 1,
            allowed_rotations_deg,
            nominal_bbox_area: bbox_area(&poly.outer),
            inflated_polygon: poly,
        }
    }

    #[test]
    fn sa_search_is_deterministic_tiny_blf_case() {
        std::env::set_var("NESTING_ENGINE_STOP_MODE", "work_budget");

        let specs = vec![
            tiny_part("a", 18.0, 10.0, vec![0, 90]),
            tiny_part("b", 12.0, 12.0, vec![0]),
            tiny_part("c", 10.0, 8.0, vec![0, 90]),
        ];
        let bin = rect_poly(30.0, 20.0);
        let cfg = SaSearchConfig {
            iters: 96,
            temp_start: 10_000,
            temp_end: 50,
            seed: 2026,
            eval_budget_sec: 2,
        };

        let run_a = run_sa_search_over_specs(&specs, &bin, 1.0, PlacerKind::Blf, cfg)
            .expect("run_a must succeed");
        let run_b = run_sa_search_over_specs(&specs, &bin, 1.0, PlacerKind::Blf, cfg)
            .expect("run_b must succeed");

        assert_eq!(run_a.0, run_b.0);
        assert_eq!(run_a.1, run_b.1);
    }

    #[test]
    fn sa_quality_fixture_improves_sheets_used() {
        std::env::set_var("NESTING_ENGINE_STOP_MODE", "work_budget");

        let specs = vec![
            tiny_part("A", 90.0, 40.0, vec![0, 90]),
            tiny_part("B", 40.0, 90.0, vec![0]),
        ];
        let bin = rect_poly(100.0, 100.0);

        let (baseline, _baseline_stats) =
            greedy_multi_sheet(&specs, &bin, 1.0, 2, PlacerKind::Blf, PartOrderPolicy::ByArea);
        assert_eq!(
            baseline.sheets_used, 2,
            "baseline fixture expectation must stay stable"
        );

        let sa_cfg = SaSearchConfig {
            iters: 128,
            temp_start: 10_000,
            temp_end: 50,
            seed: 2026,
            eval_budget_sec: 2,
        };
        let (sa_result, _sa_stats) =
            run_sa_search_over_specs(&specs, &bin, 1.0, PlacerKind::Blf, sa_cfg)
                .expect("SA run must succeed on quality fixture");

        assert!(
            sa_result.sheets_used < baseline.sheets_used,
            "SA must improve sheets_used on quality fixture"
        );
        assert_eq!(
            sa_result.sheets_used, 1,
            "SA quality fixture expectation must stay stable"
        );
    }
}
