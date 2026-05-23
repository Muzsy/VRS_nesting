use serde::{Deserialize, Serialize};

use super::state::PlacementTransform;

/// Optimizer move skeleton. Place/Move/Reinsert/Rotate variants cover the
/// four canonical search operations; no candidate generation or collision
/// logic lives here — those are JG-08+ scope.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CandidateMove {
    /// Place an unplaced instance at the given sheet and transform.
    Place {
        instance_id: String,
        sheet_index: usize,
        transform: PlacementTransform,
    },
    /// Move an already-placed instance to a different sheet and/or transform.
    Move {
        instance_id: String,
        to_sheet_index: usize,
        to_transform: PlacementTransform,
    },
    /// Reinsert an instance (may be placed or unplaced) at a new location.
    Reinsert {
        instance_id: String,
        sheet_index: usize,
        transform: PlacementTransform,
    },
    /// Rotate a placed or candidate instance to a new rotation.
    Rotate {
        instance_id: String,
        new_rotation_deg: i64,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(x: f64, y: f64, rot: i64) -> PlacementTransform {
        PlacementTransform { x, y, rotation_deg: rot }
    }

    #[test]
    fn candidate_move_place_creates() {
        let mv = CandidateMove::Place {
            instance_id: "A__0001".to_string(),
            sheet_index: 0,
            transform: t(0.0, 0.0, 0),
        };
        let json = serde_json::to_string(&mv).expect("serialize");
        assert!(json.contains("Place"));
        assert!(json.contains("A__0001"));
    }

    #[test]
    fn candidate_move_all_variants_create() {
        let variants: Vec<CandidateMove> = vec![
            CandidateMove::Place { instance_id: "A".to_string(), sheet_index: 0, transform: t(0.0, 0.0, 0) },
            CandidateMove::Move { instance_id: "B".to_string(), to_sheet_index: 1, to_transform: t(10.0, 0.0, 90) },
            CandidateMove::Reinsert { instance_id: "C".to_string(), sheet_index: 0, transform: t(20.0, 0.0, 180) },
            CandidateMove::Rotate { instance_id: "D".to_string(), new_rotation_deg: 270 },
        ];
        assert_eq!(variants.len(), 4);
        for mv in &variants {
            let json = serde_json::to_string(mv).expect("serialize");
            assert!(!json.is_empty());
        }
    }

    #[test]
    fn candidate_move_json_stable() {
        let mv = CandidateMove::Rotate { instance_id: "X__0001".to_string(), new_rotation_deg: 90 };
        let j1 = serde_json::to_string(&mv).expect("s1");
        let j2 = serde_json::to_string(&mv).expect("s2");
        assert_eq!(j1, j2);
    }
}
