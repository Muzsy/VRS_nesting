#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SaConfig {
    pub iters: u64,
    pub temp_start: u64,
    pub temp_end: u64,
    pub seed: u64,
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
    use super::{SaConfig, SaState, run_sa_core};

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
}
