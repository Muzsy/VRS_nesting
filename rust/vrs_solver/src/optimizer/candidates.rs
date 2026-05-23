use crate::geometry::EPS;

/// Candidate point for item placement. `(x, y)` is the bbox-min corner
/// at which the next item's bounding box would be tried.
#[derive(Debug, Clone)]
pub struct CandidatePoint {
    pub sheet_index: usize,
    pub x: f64,
    pub y: f64,
}

/// Axis-aligned placed bounding box (bbox-min coords, Phase 1 rectangular items only).
#[derive(Debug, Clone)]
pub struct PlacedBbox {
    pub sheet_index: usize,
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
}

impl PlacedBbox {
    /// Rect-rect overlap — exact for Phase 1 rectangular items at 0/90/180/270°.
    pub fn overlaps(&self, other: &PlacedBbox) -> bool {
        if self.sheet_index != other.sheet_index {
            return false;
        }
        self.x1 < other.x2 - EPS
            && self.x2 > other.x1 + EPS
            && self.y1 < other.y2 - EPS
            && self.y2 > other.y1 + EPS
    }
}

/// Generate sorted, deduplicated placement candidate points.
///
/// Each sheet contributes the origin `(0, 0)`. Each placed bbox contributes
/// its right-side, top-side, and top-right-corner points.
/// Result sorted by `(sheet_index ASC, y ASC, x ASC)`, deduplicated by EPS proximity.
pub fn generate_candidates(sheet_count: usize, placed: &[PlacedBbox]) -> Vec<CandidatePoint> {
    let mut pts: Vec<CandidatePoint> = Vec::with_capacity(sheet_count + placed.len() * 3);
    for s in 0..sheet_count {
        pts.push(CandidatePoint { sheet_index: s, x: 0.0, y: 0.0 });
    }
    for pb in placed {
        pts.push(CandidatePoint { sheet_index: pb.sheet_index, x: pb.x2, y: pb.y1 });
        pts.push(CandidatePoint { sheet_index: pb.sheet_index, x: pb.x1, y: pb.y2 });
        pts.push(CandidatePoint { sheet_index: pb.sheet_index, x: pb.x2, y: pb.y2 });
    }
    pts.sort_by(|a, b| {
        a.sheet_index
            .cmp(&b.sheet_index)
            .then_with(|| a.y.partial_cmp(&b.y).unwrap_or(std::cmp::Ordering::Equal))
            .then_with(|| a.x.partial_cmp(&b.x).unwrap_or(std::cmp::Ordering::Equal))
    });
    pts.dedup_by(|a, b| {
        a.sheet_index == b.sheet_index
            && (a.x - b.x).abs() < EPS
            && (a.y - b.y).abs() < EPS
    });
    pts
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn candidates_origin_for_every_sheet() {
        let cands = generate_candidates(3, &[]);
        assert_eq!(cands.len(), 3);
        for s in 0..3 {
            assert!(cands.iter().any(|c| c.sheet_index == s && c.x == 0.0 && c.y == 0.0));
        }
    }

    #[test]
    fn candidates_from_placed_bbox_adds_three_points() {
        let placed = vec![PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 100.0, y2: 50.0 }];
        let cands = generate_candidates(1, &placed);
        assert!(cands.iter().any(|c| c.sheet_index == 0 && (c.x - 100.0).abs() < 1e-6 && c.y.abs() < 1e-6));
        assert!(cands.iter().any(|c| c.sheet_index == 0 && c.x.abs() < 1e-6 && (c.y - 50.0).abs() < 1e-6));
        assert!(cands.iter().any(|c| c.sheet_index == 0 && (c.x - 100.0).abs() < 1e-6 && (c.y - 50.0).abs() < 1e-6));
    }

    #[test]
    fn candidates_sorted_by_sheet_y_x() {
        let placed = vec![PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 50.0, y2: 30.0 }];
        let cands = generate_candidates(2, &placed);
        for w in cands.windows(2) {
            let a = &w[0];
            let b = &w[1];
            let ok = a.sheet_index < b.sheet_index
                || (a.sheet_index == b.sheet_index && a.y < b.y + 1e-12)
                || (a.sheet_index == b.sheet_index && (a.y - b.y).abs() < 1e-6 && a.x <= b.x + 1e-12);
            assert!(ok, "not sorted: ({},{}) vs ({},{})", a.x, a.y, b.x, b.y);
        }
    }

    #[test]
    fn placed_bbox_overlap_same_sheet() {
        let a = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 50.0, y2: 50.0 };
        let b = PlacedBbox { sheet_index: 0, x1: 25.0, y1: 25.0, x2: 75.0, y2: 75.0 };
        assert!(a.overlaps(&b));
    }

    #[test]
    fn placed_bbox_no_overlap_adjacent() {
        let a = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 50.0, y2: 50.0 };
        let b = PlacedBbox { sheet_index: 0, x1: 50.0, y1: 0.0, x2: 100.0, y2: 50.0 };
        assert!(!a.overlaps(&b));
    }

    #[test]
    fn placed_bbox_no_overlap_different_sheets() {
        let a = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 50.0, y2: 50.0 };
        let b = PlacedBbox { sheet_index: 1, x1: 0.0, y1: 0.0, x2: 50.0, y2: 50.0 };
        assert!(!a.overlaps(&b));
    }
}
