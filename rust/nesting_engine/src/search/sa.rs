use std::sync::Once;
use std::time::{Duration, Instant};

use crate::{
    geometry::types::Polygon64,
    multi_bin::{
        greedy::{CompactionMode, PartInPartMode, PartOrderPolicy, PlacerKind},
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
    pub time_limit_sec: u64,
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
    remnant_axis: u128,
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

#[allow(dead_code)]
pub fn run_sa_core<F>(
    initial_state: SaState,
    rotation_options_len: &[u8],
    config: SaConfig,
    mut evaluate: F,
) -> Result<SaRunResult, String>
where
    F: FnMut(&SaState) -> i64,
{
    run_sa_core_with_stop_hook(
        initial_state,
        rotation_options_len,
        config,
        &mut evaluate,
        || false,
    )
}

#[allow(dead_code)]
fn run_sa_core_with_stop_hook<F, S>(
    initial_state: SaState,
    rotation_options_len: &[u8],
    config: SaConfig,
    mut evaluate: F,
    should_stop: S,
) -> Result<SaRunResult, String>
where
    F: FnMut(&SaState) -> i64,
    S: FnMut() -> bool,
{
    let (run, _best_payload) = run_sa_core_with_stop_hook_and_payload(
        initial_state,
        rotation_options_len,
        config,
        |state| Ok((evaluate(state), ())),
        should_stop,
    )?;
    Ok(run)
}

fn run_sa_core_with_stop_hook_and_payload<F, S, T>(
    initial_state: SaState,
    rotation_options_len: &[u8],
    config: SaConfig,
    mut evaluate: F,
    mut should_stop: S,
) -> Result<(SaRunResult, T), String>
where
    F: FnMut(&SaState) -> Result<(i64, T), String>,
    S: FnMut() -> bool,
    T: Clone,
{
    validate_state(&initial_state, rotation_options_len)?;

    let mut rng = SplitMix64::new(config.seed);
    let mut current_state = initial_state.clone();
    let (mut current_cost, mut current_payload) = evaluate(&current_state)?;
    let mut best_state = current_state.clone();
    let mut best_cost = current_cost;
    let mut best_payload = current_payload.clone();

    for iter in 0..config.iters {
        if should_stop() {
            break;
        }
        let mut candidate = current_state.clone();
        apply_neighbor(&mut candidate, rotation_options_len, &mut rng);

        let (candidate_cost, candidate_payload) = evaluate(&candidate)?;
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
            current_payload = candidate_payload;
        }

        if current_cost < best_cost
            || (current_cost == best_cost
                && lexicographically_precedes(&current_state, &best_state))
        {
            best_state = current_state.clone();
            best_cost = current_cost;
            best_payload = current_payload.clone();
        }
    }

    Ok((
        SaRunResult {
            best_state,
            best_cost,
            final_state: current_state,
            final_cost: current_cost,
        },
        best_payload,
    ))
}

/// Fractional safety margin reserved from `time_limit_sec` before computing
/// the SA evaluation-slot budget. Controlled by
/// `NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC` (default 0.0 = unchanged behavior).
/// Valid range: [0.0, 0.5). Any invalid or out-of-range value falls back to 0.0.
/// When > 0, the clamp leaves `ceil(time_limit_sec * frac)` seconds of wall
/// time unallocated so that solver output serialization + worker finalization
/// do not get pre-empted by the final SA evaluation.
fn sa_safety_margin_frac() -> f64 {
    let raw = match std::env::var("NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC") {
        Ok(v) => v,
        Err(_) => return 0.0_f64,
    };
    let parsed: f64 = match raw.trim().parse() {
        Ok(v) => v,
        Err(_) => return 0.0_f64,
    };
    if !parsed.is_finite() || parsed < 0.0 || parsed >= 0.5 {
        return 0.0_f64;
    }
    parsed
}

pub fn clamp_sa_iters_by_time_limit_and_eval_budget(
    requested_iters: u64,
    time_limit_sec: u64,
    eval_budget_sec: u64,
) -> u64 {
    if eval_budget_sec == 0 {
        return requested_iters;
    }

    // Optional safety reserve: subtract `ceil(time_limit_sec * frac)` seconds
    // from the usable budget so the SA eval loop cannot monopolize the full
    // wall-clock window. Default frac = 0.0 preserves existing behavior.
    let margin_frac = sa_safety_margin_frac();
    let reserve_sec: u64 = if margin_frac > 0.0 && time_limit_sec > 0 {
        (time_limit_sec as f64 * margin_frac).ceil() as u64
    } else {
        0
    };
    let usable_time_sec = time_limit_sec.saturating_sub(reserve_sec);

    // Hard SA budget model: `1 + iters` evaluations.
    // 1 initial eval before the loop and `iters` candidate evals in-loop.
    // Clamp by evaluation slots: max_evals = floor(usable_time_sec / eval_budget_sec),
    // max_iters = max_evals.saturating_sub(1), effective_iters = min(requested_iters, max_iters).
    let max_evals = usable_time_sec / eval_budget_sec;
    let max_iters = max_evals.saturating_sub(1);
    requested_iters.min(max_iters)
}

type SaEvaluatedLayout = (MultiSheetResult, Option<NfpPlacerStatsV1>);

pub fn run_sa_search_over_specs(
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    grid_step_mm: f64,
    placer_kind: PlacerKind,
    config: SaSearchConfig,
    part_in_part_mode: PartInPartMode,
    compaction_mode: CompactionMode,
) -> Result<(MultiSheetResult, Option<NfpPlacerStatsV1>), String> {
    let sa_start = Instant::now();
    let mut eval_count: u64 = 0;
    let profiling = matches!(
        std::env::var("NESTING_ENGINE_BLF_PROFILE"),
        Ok(v) if v == "1"
    );

    let result = run_sa_search_over_specs_with_eval_hook(
        base_specs,
        bin,
        grid_step_mm,
        placer_kind,
        config,
        part_in_part_mode,
        compaction_mode,
        || { eval_count += 1; },
    );

    if profiling {
        let sa_wall_ms = sa_start.elapsed().as_secs_f64() * 1000.0;
        eprintln!(
            "SA_PROFILE_V1 {{\"sa_eval_count\":{},\"sa_wall_ms\":{:.1},\"sa_iters_configured\":{},\"sa_eval_budget_sec\":{},\"sa_time_limit_sec\":{}}}",
            eval_count, sa_wall_ms, config.iters, config.eval_budget_sec, config.time_limit_sec
        );
    }

    result
}

fn run_sa_search_over_specs_with_eval_hook<E>(
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    grid_step_mm: f64,
    placer_kind: PlacerKind,
    config: SaSearchConfig,
    part_in_part_mode: PartInPartMode,
    compaction_mode: CompactionMode,
    mut on_eval: E,
) -> Result<(MultiSheetResult, Option<NfpPlacerStatsV1>), String>
where
    E: FnMut(),
{
    if config.eval_budget_sec == 0 {
        return Err("sa eval budget must be >= 1 second".to_string());
    }
    if config.time_limit_sec == 0 {
        return Err("sa time limit must be >= 1 second".to_string());
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
            part_in_part_mode,
            compaction_mode,
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
        iters: clamp_sa_iters_by_time_limit_and_eval_budget(
            config.iters,
            config.time_limit_sec,
            config.eval_budget_sec,
        ),
        temp_start: config.temp_start,
        temp_end: config.temp_end,
        seed: config.seed,
    };
    let deadline = Instant::now()
        .checked_add(Duration::from_secs(config.time_limit_sec))
        .ok_or_else(|| "sa deadline overflow".to_string())?;

    let (_run, best_payload) = run_sa_core_with_stop_hook_and_payload(
        initial_state,
        &rotation_options_len,
        core_cfg,
        |state| {
            on_eval();
            eval_state_cost_with_result(
                state,
                base_specs,
                bin,
                grid_step_mm,
                placer_kind,
                config.eval_budget_sec,
                cost_encoding,
                part_in_part_mode,
                compaction_mode,
            )
        },
        || Instant::now() >= deadline,
    )?;

    Ok(best_payload)
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
        const MAX_SCORE_PER_SHEET_PPM: u128 = 1_000_000;

        let axis = u128::from(total_instances).saturating_add(1);
        let remnant_axis = u128::from(total_instances)
            .saturating_mul(MAX_SCORE_PER_SHEET_PPM)
            .saturating_add(1);
        let sheets_weight = remnant_axis;
        let unplaced_weight = axis
            .checked_mul(axis)
            .and_then(|v| v.checked_mul(MAX_SCORE_PER_SHEET_PPM))
            .ok_or_else(|| "sa cost encoding overflow while computing weights".to_string())?;

        let max_total = u128::from(total_instances);
        let max_remnant_penalty = remnant_axis.saturating_sub(1);
        let max_cost = max_total
            .checked_mul(unplaced_weight)
            .and_then(|v| v.checked_add(max_total.checked_mul(sheets_weight)?))
            .and_then(|v| v.checked_add(max_remnant_penalty))
            .ok_or_else(|| "sa cost encoding overflow while computing max cost".to_string())?;
        if max_cost > i64::MAX as u128 {
            return Err("sa cost encoding exceeds i64 range for this input size".to_string());
        }

        Ok(Self {
            unplaced_weight,
            sheets_weight,
            remnant_axis,
        })
    }

    fn encode(self, unplaced_count: u64, sheets_used: u64, remnant_value_ppm: u64) -> Result<i64, String> {
        let remnant_cap = self.remnant_axis.saturating_sub(1);
        let remnant_value = u128::from(remnant_value_ppm).min(remnant_cap);
        let remnant_penalty = remnant_cap.saturating_sub(remnant_value);
        let cost = u128::from(unplaced_count)
            .checked_mul(self.unplaced_weight)
            .and_then(|v| v.checked_add(u128::from(sheets_used).checked_mul(self.sheets_weight)?))
            .and_then(|v| v.checked_add(remnant_penalty))
            .ok_or_else(|| "sa cost encoding overflow during evaluation".to_string())?;

        i64::try_from(cost).map_err(|_| "sa cost value does not fit into i64".to_string())
    }
}

fn eval_state_cost_with_result(
    state: &SaState,
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    grid_step_mm: f64,
    placer_kind: PlacerKind,
    eval_budget_sec: u64,
    cost_encoding: CostEncoding,
    part_in_part_mode: PartInPartMode,
    compaction_mode: CompactionMode,
) -> Result<(i64, SaEvaluatedLayout), String> {
    let specs = specs_for_state(base_specs, state);
    let (result, stats) = greedy_multi_sheet(
        &specs,
        bin,
        grid_step_mm,
        eval_budget_sec,
        placer_kind,
        PartOrderPolicy::ByInputOrder,
        part_in_part_mode,
        compaction_mode,
    );

    let unplaced_count = u64::try_from(result.unplaced.len())
        .map_err(|_| "unplaced item count does not fit into u64".to_string())?;
    let sheets_used = u64::try_from(result.sheets_used)
        .map_err(|_| "sheet count does not fit into u64".to_string())?;
    let remnant_value_ppm = result.remnant_value_ppm;

    let cost = cost_encoding.encode(unplaced_count, sheets_used, remnant_value_ppm)?;
    Ok((cost, (result, stats)))
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
    let can_move = n >= 2;
    let can_rotate = rotation_options_len.iter().any(|&len| len > 1);

    if !can_swap && !can_move && !can_rotate {
        return;
    }

    let mut op_count = 0usize;
    if can_swap {
        op_count += 1;
    }
    if can_move {
        op_count += 1;
    }
    if can_rotate {
        op_count += 1;
    }

    let mut selected = random_index(rng, op_count);
    if can_swap {
        if selected == 0 {
            apply_swap(state, rng);
            return;
        }
        selected -= 1;
    }
    if can_move {
        if selected == 0 {
            apply_move(state, rng);
            return;
        }
        selected -= 1;
    }
    if can_rotate && selected == 0 {
        apply_rotate(state, rotation_options_len, rng);
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

fn apply_move(state: &mut SaState, rng: &mut SplitMix64) {
    let n = state.order.len();
    if n < 2 {
        return;
    }

    let from = random_index(rng, n);
    let mut to = random_index(rng, n - 1);
    if to >= from {
        to += 1;
    }

    let moved = state.order.remove(from);
    state.order.insert(to, moved);
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
    use std::cell::Cell;

    use super::{
        CostEncoding, apply_move, clamp_sa_iters_by_time_limit_and_eval_budget, run_sa_core,
        run_sa_core_with_stop_hook, run_sa_search_over_specs,
        run_sa_search_over_specs_with_eval_hook, SaConfig, SaSearchConfig, SaState, SplitMix64,
    };
    use crate::{
        multi_bin::{
            greedy::CompactionMode, greedy::PartInPartMode, greedy::PartOrderPolicy,
            greedy::PlacerKind,
            greedy_multi_sheet,
        },
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
            time_limit_sec: 300,
            eval_budget_sec: 2,
        };

        let run_a = run_sa_search_over_specs(
            &specs,
            &bin,
            1.0,
            PlacerKind::Blf,
            cfg,
            PartInPartMode::Off,
            CompactionMode::Off,
        )
            .expect("run_a must succeed");
        let run_b = run_sa_search_over_specs(
            &specs,
            &bin,
            1.0,
            PlacerKind::Blf,
            cfg,
            PartInPartMode::Off,
            CompactionMode::Off,
        )
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

        let (baseline, _baseline_stats) = greedy_multi_sheet(
            &specs,
            &bin,
            1.0,
            2,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        assert_eq!(
            baseline.sheets_used, 2,
            "baseline fixture expectation must stay stable"
        );

        let sa_cfg = SaSearchConfig {
            iters: 128,
            temp_start: 10_000,
            temp_end: 50,
            seed: 2026,
            time_limit_sec: 300,
            eval_budget_sec: 2,
        };
        let (sa_result, _sa_stats) = run_sa_search_over_specs(
            &specs,
            &bin,
            1.0,
            PlacerKind::Blf,
            sa_cfg,
            PartInPartMode::Off,
            CompactionMode::Off,
        )
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

    #[test]
    fn sa_prefers_higher_remnant_value_when_sheets_tie() {
        let encoding = CostEncoding::new(8).expect("encoding must fit into i64");
        let lower_remnant_cost = encoding
            .encode(0, 1, 300_000)
            .expect("encoding low remnant must succeed");
        let higher_remnant_cost = encoding
            .encode(0, 1, 800_000)
            .expect("encoding high remnant must succeed");

        assert!(
            higher_remnant_cost < lower_remnant_cost,
            "for equal unplaced and sheets, higher remnant_value_ppm must be preferred"
        );
    }

    #[test]
    fn sa_move_neighbor_preserves_permutation() {
        let mut state = SaState {
            order: vec![0, 1, 2, 3, 4],
            rot_choice: vec![0, 1, 0, 1, 0],
        };
        let original_order = state.order.clone();
        let original_rot_choice = state.rot_choice.clone();
        let mut rng = SplitMix64::new(2026);

        apply_move(&mut state, &mut rng);

        assert_ne!(
            state.order, original_order,
            "move neighbor must change order for len>=2"
        );
        assert_eq!(
            state.rot_choice, original_rot_choice,
            "move neighbor must not mutate rot_choice"
        );

        let mut expected = original_order;
        let mut actual = state.order.clone();
        expected.sort_unstable();
        actual.sort_unstable();
        assert_eq!(
            actual, expected,
            "move neighbor must preserve the same permutation elements"
        );
    }

    #[test]
    fn sa_iters_clamp_allows_zero_when_only_initial_eval_fits() {
        assert_eq!(
            clamp_sa_iters_by_time_limit_and_eval_budget(256, 1, 1),
            0,
            "one eval slot can only run the initial evaluation"
        );
        assert_eq!(
            clamp_sa_iters_by_time_limit_and_eval_budget(256, 2, 1),
            1,
            "two eval slots allow exactly one SA iteration"
        );
        assert_eq!(
            clamp_sa_iters_by_time_limit_and_eval_budget(256, 60, 6),
            9,
            "10 eval slots minus the single initial eval leaves 9 iterations"
        );
    }

    #[test]
    fn sa_core_stop_hook_can_short_circuit_before_first_iter() {
        let initial = SaState {
            order: vec![0, 1, 2],
            rot_choice: vec![0, 0, 0],
        };
        let rotation_options_len = vec![1, 1, 1];
        let config = SaConfig {
            iters: 64,
            temp_start: 10_000,
            temp_end: 50,
            seed: 11,
        };

        let mut eval_calls = 0u64;
        let run = run_sa_core_with_stop_hook(
            initial.clone(),
            &rotation_options_len,
            config,
            |state| {
                eval_calls = eval_calls.saturating_add(1);
                eval_cost(state)
            },
            || true,
        )
        .expect("run must succeed");

        assert_eq!(eval_calls, 1, "only the initial evaluation must run");
        assert_eq!(run.final_state, initial, "final state must stay initial");
        assert_eq!(run.best_state, initial, "best state must stay initial");
    }

    #[test]
    fn sa_search_zero_iter_budget_returns_initial_eval_result() {
        std::env::set_var("NESTING_ENGINE_STOP_MODE", "work_budget");

        let specs = vec![
            tiny_part("a", 18.0, 10.0, vec![0, 90]),
            tiny_part("b", 12.0, 12.0, vec![0]),
            tiny_part("c", 10.0, 8.0, vec![0, 90]),
        ];
        let bin = rect_poly(30.0, 20.0);
        let cfg = SaSearchConfig {
            iters: 256,
            temp_start: 10_000,
            temp_end: 50,
            seed: 2026,
            time_limit_sec: 1,
            eval_budget_sec: 1,
        };
        assert_eq!(
            clamp_sa_iters_by_time_limit_and_eval_budget(
                cfg.iters,
                cfg.time_limit_sec,
                cfg.eval_budget_sec
            ),
            0
        );

        let expected = greedy_multi_sheet(
            &specs,
            &bin,
            1.0,
            cfg.eval_budget_sec,
            PlacerKind::Blf,
            PartOrderPolicy::ByInputOrder,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        let actual = run_sa_search_over_specs(
            &specs,
            &bin,
            1.0,
            PlacerKind::Blf,
            cfg,
            PartInPartMode::Off,
            CompactionMode::Off,
        )
        .expect("SA run must succeed even when only initial eval fits");

        assert_eq!(
            actual, expected,
            "zero-iter SA must return the initial evaluated placement result"
        );
    }

    #[test]
    fn sa_search_reuses_best_evaluated_result_without_final_rerun() {
        std::env::set_var("NESTING_ENGINE_STOP_MODE", "work_budget");

        let specs = vec![
            tiny_part("a", 18.0, 10.0, vec![0, 90]),
            tiny_part("b", 12.0, 12.0, vec![0]),
            tiny_part("c", 10.0, 8.0, vec![0, 90]),
        ];
        let bin = rect_poly(30.0, 20.0);
        let cfg = SaSearchConfig {
            iters: 64,
            temp_start: 10_000,
            temp_end: 50,
            seed: 2026,
            time_limit_sec: 5,
            eval_budget_sec: 1,
        };
        let effective_iters = clamp_sa_iters_by_time_limit_and_eval_budget(
            cfg.iters,
            cfg.time_limit_sec,
            cfg.eval_budget_sec,
        );
        let eval_calls = Cell::new(0_u64);

        let _run = run_sa_search_over_specs_with_eval_hook(
            &specs,
            &bin,
            1.0,
            PlacerKind::Blf,
            cfg,
            PartInPartMode::Off,
            CompactionMode::Off,
            || eval_calls.set(eval_calls.get().saturating_add(1)),
        )
        .expect("SA run must succeed");

        assert_eq!(
            eval_calls.get(),
            1 + effective_iters,
            "SA must not execute an additional final rerun beyond initial+iter evaluations"
        );
    }
}
