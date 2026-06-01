use std::time::Instant;

/// Why the repair loop stopped.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StopReason {
    /// No more violations remain — layout is valid.
    Converged,
    /// Reached max_iterations limit.
    MaxIterations,
    /// Elapsed time >= time_limit_s.
    TimeLimit,
}

/// Deterministic stopping policy for the repair loop.
///
/// Stops when: `iteration >= max_iterations` OR `elapsed >= time_limit_s`.
/// Phase 1: time_limit_s is derived from SolverInput; max_iterations caps
/// deterministic repair passes so identical inputs always terminate identically.
pub struct StoppingPolicy {
    pub max_iterations: usize,
    pub time_limit_s: f64,
    start: Instant,
    iteration: usize,
}

impl StoppingPolicy {
    pub fn new(max_iterations: usize, time_limit_s: f64) -> Self {
        Self {
            max_iterations,
            time_limit_s,
            start: Instant::now(),
            iteration: 0,
        }
    }

    /// Advance one iteration. Returns `true` if the policy says stop.
    pub fn tick(&mut self) -> bool {
        self.iteration += 1;
        self.should_stop()
    }

    /// Check stop condition without advancing iteration count.
    pub fn should_stop(&self) -> bool {
        self.iteration >= self.max_iterations || self.elapsed_s() >= self.time_limit_s
    }

    pub fn elapsed_s(&self) -> f64 {
        self.start.elapsed().as_secs_f64()
    }

    pub fn iteration(&self) -> usize {
        self.iteration
    }

    pub fn stop_reason(&self) -> StopReason {
        if self.elapsed_s() >= self.time_limit_s {
            StopReason::TimeLimit
        } else if self.iteration >= self.max_iterations {
            StopReason::MaxIterations
        } else {
            StopReason::Converged
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stopping_policy_max_iterations() {
        let mut p = StoppingPolicy::new(3, 1000.0);
        assert!(!p.tick()); // iter=1, 1>=3 false
        assert!(!p.tick()); // iter=2, 2>=3 false
        assert!(p.tick()); // iter=3, 3>=3 true → stop
    }

    #[test]
    fn stopping_policy_time_limit_zero() {
        let p = StoppingPolicy::new(1000, 0.0);
        // elapsed() >= 0.0 is always true
        assert!(p.should_stop());
    }

    #[test]
    fn stopping_policy_converged_reason() {
        let p = StoppingPolicy::new(1000, 1000.0);
        assert_eq!(p.stop_reason(), StopReason::Converged);
    }

    #[test]
    fn stopping_policy_max_iter_reason() {
        let mut p = StoppingPolicy::new(2, 1000.0);
        p.tick();
        p.tick();
        assert_eq!(p.stop_reason(), StopReason::MaxIterations);
    }

    #[test]
    fn stopping_policy_iteration_counter() {
        let mut p = StoppingPolicy::new(100, 1000.0);
        p.tick();
        p.tick();
        assert_eq!(p.iteration(), 2);
    }
}
