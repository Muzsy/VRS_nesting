use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PlacementTransform {
    pub x: f64,
    pub y: f64,
    pub rotation_deg: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlacedItem {
    pub instance_id: String,
    pub part_id: String,
    pub sheet_index: usize,
    pub transform: PlacementTransform,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnplacedItem {
    pub instance_id: String,
    pub part_id: String,
    pub reason: String,
}

/// Optimizer internal layout state.  Not the v1 output contract — convert via
/// `io::SolverOutput` for the JSON API boundary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LayoutState {
    pub placed: Vec<PlacedItem>,
    pub unplaced: Vec<UnplacedItem>,
    /// Number of available sheet slots (expanded, stable index base).
    pub sheet_count: usize,
    /// RNG seed forwarded from SolverInput for determinism tracing.
    pub seed: i64,
}

impl LayoutState {
    pub fn new(sheet_count: usize, seed: i64) -> Self {
        Self { placed: vec![], unplaced: vec![], sheet_count, seed }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn transform(x: f64, y: f64, rot: i64) -> PlacementTransform {
        PlacementTransform { x, y, rotation_deg: rot }
    }

    fn placed(id: &str, part: &str, sheet: usize, t: PlacementTransform) -> PlacedItem {
        PlacedItem {
            instance_id: id.to_string(),
            part_id: part.to_string(),
            sheet_index: sheet,
            transform: t,
        }
    }

    fn unplaced(id: &str, part: &str, reason: &str) -> UnplacedItem {
        UnplacedItem {
            instance_id: id.to_string(),
            part_id: part.to_string(),
            reason: reason.to_string(),
        }
    }

    #[test]
    fn placement_transform_roundtrip() {
        let t = transform(12.5, 34.0, 90);
        let json = serde_json::to_string(&t).expect("serialize");
        let t2: PlacementTransform = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(t, t2);
    }

    #[test]
    fn placed_item_retains_transform() {
        let t = transform(1.0, 2.0, 180);
        let item = placed("A__0001", "A", 0, t.clone());
        assert_eq!(item.transform, t);
        assert_eq!(item.sheet_index, 0);
        assert_eq!(item.instance_id, "A__0001");
    }

    #[test]
    fn layout_state_placed_unplaced_separation() {
        let mut state = LayoutState::new(3, 42);
        state.placed.push(placed("A__0001", "A", 0, transform(0.0, 0.0, 0)));
        state.placed.push(placed("B__0001", "B", 1, transform(10.0, 0.0, 90)));
        state.unplaced.push(unplaced("C__0001", "C", "NO_CAPACITY"));
        assert_eq!(state.placed.len(), 2);
        assert_eq!(state.unplaced.len(), 1);
    }

    #[test]
    fn state_json_serialization() {
        let mut state = LayoutState::new(2, 7);
        state.placed.push(placed("P__0001", "P", 0, transform(5.0, 3.0, 0)));
        let json = serde_json::to_string(&state).expect("serialize");
        assert!(json.contains("placed"));
        assert!(json.contains("P__0001"));
    }

    #[test]
    fn deterministic_state_ordering() {
        let build = || {
            let mut s = LayoutState::new(1, 0);
            s.placed.push(placed("A__0001", "A", 0, transform(0.0, 0.0, 0)));
            s.placed.push(placed("B__0001", "B", 0, transform(50.0, 0.0, 0)));
            s
        };
        let json1 = serde_json::to_string(&build()).expect("s1");
        let json2 = serde_json::to_string(&build()).expect("s2");
        assert_eq!(json1, json2);
    }
}
