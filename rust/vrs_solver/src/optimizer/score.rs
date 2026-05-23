use serde::{Deserialize, Serialize};

use super::state::LayoutState;

/// Diagnostic breakdown of the optimizer objective.
/// Phase 1 skeleton — no score optimization logic here (JG-10+ scope).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObjectiveBreakdown {
    pub placed_count: usize,
    pub unplaced_count: usize,
    pub sheet_count_used: usize,
    /// Placeholder for future weighted penalty terms (JG-10+).
    pub penalty_placeholder: f64,
}

impl ObjectiveBreakdown {
    pub fn from_layout_state(state: &LayoutState) -> Self {
        let sheet_count_used = state
            .placed
            .iter()
            .map(|p| p.sheet_index)
            .max()
            .map(|v| v + 1)
            .unwrap_or(0);
        Self {
            placed_count: state.placed.len(),
            unplaced_count: state.unplaced.len(),
            sheet_count_used,
            penalty_placeholder: 0.0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::optimizer::state::{PlacedItem, PlacementTransform, UnplacedItem};

    fn placed(id: &str, sheet: usize) -> PlacedItem {
        PlacedItem {
            instance_id: id.to_string(),
            part_id: "P".to_string(),
            sheet_index: sheet,
            transform: PlacementTransform { x: 0.0, y: 0.0, rotation_deg: 0 },
        }
    }

    fn unplaced(id: &str) -> UnplacedItem {
        UnplacedItem {
            instance_id: id.to_string(),
            part_id: "P".to_string(),
            reason: "NO_CAPACITY".to_string(),
        }
    }

    #[test]
    fn objective_breakdown_from_state_counts() {
        let mut state = LayoutState::new(3, 0);
        state.placed.push(placed("A__0001", 0));
        state.placed.push(placed("B__0001", 2));
        state.unplaced.push(unplaced("C__0001"));
        let bd = ObjectiveBreakdown::from_layout_state(&state);
        assert_eq!(bd.placed_count, 2);
        assert_eq!(bd.unplaced_count, 1);
        assert_eq!(bd.sheet_count_used, 3); // max index=2, +1=3
    }

    #[test]
    fn objective_breakdown_empty_state() {
        let state = LayoutState::new(0, 0);
        let bd = ObjectiveBreakdown::from_layout_state(&state);
        assert_eq!(bd.placed_count, 0);
        assert_eq!(bd.unplaced_count, 0);
        assert_eq!(bd.sheet_count_used, 0);
    }

    #[test]
    fn objective_breakdown_sheet_count_used_max_index_plus_one() {
        let mut state = LayoutState::new(5, 0);
        state.placed.push(placed("A__0001", 0));
        state.placed.push(placed("B__0001", 1));
        state.placed.push(placed("C__0001", 4));
        let bd = ObjectiveBreakdown::from_layout_state(&state);
        assert_eq!(bd.sheet_count_used, 5); // max index=4, +1=5
    }
}
