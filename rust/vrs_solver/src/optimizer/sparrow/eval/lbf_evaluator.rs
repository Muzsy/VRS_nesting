use super::*;

pub(crate) struct LBFEvaluator<'a> {
    pub(crate) inst: &'a SPInstance,
    pub(crate) sheet: &'a SheetShape,
    pub(crate) sheet_idx: usize,
    pub(crate) session: &'a CdeCandidateSession,
}

impl<'a> LBFEvaluator<'a> {
    pub(crate) fn score_lbf_candidate(
        &self,
        rmx: f64,
        rmy: f64,
        rot: f64,
    ) -> Option<ScoredPlacement> {
        let (rw, rh) = dims_for_rotation(self.inst.part.width, self.inst.part.height, rot);
        if rmx < self.sheet.min_x - 1e-9
            || rmy < self.sheet.min_y - 1e-9
            || rmx + rw > self.sheet.max_x + 1e-9
            || rmy + rh > self.sheet.max_y + 1e-9
        {
            return None;
        }
        let (ax, ay) = placement_anchor_from_rect_min(
            rmx,
            rmy,
            self.inst.part.width,
            self.inst.part.height,
            rot,
        );
        let shape = prepare_shape_native(&self.inst.part, ax, ay, rot).ok()?;
        let res = self.session.query(&shape);
        if res.unsupported {
            return None;
        }
        let placement = SparrowPlacement {
            instance_idx: self.inst.idx,
            sheet_index: self.sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        };
        let lbf_quality = (rmx - self.sheet.min_x).max(0.0) * 10.0
            + (rmy - self.sheet.min_y).max(0.0)
            + (self.sheet_idx as f64) * 1e-6;
        if res.is_clear() {
            return Some(ScoredPlacement {
                score: lbf_quality,
                collision_loss: 0.0,
                is_clear: true,
                placement,
            });
        }
        // Bottom-left-fill constructor: CDE owns the clear/collision verdict; a
        // cheap boundary-spill + neighbour-count term only orders the rare
        // infeasible candidate so the LBF keeps descending toward a clear spot.
        let mut loss = if res.boundary_collision {
            ((self.sheet.min_x - shape.min_x).max(0.0)
                + (self.sheet.min_y - shape.min_y).max(0.0)
                + (shape.max_x - self.sheet.max_x).max(0.0)
                + (shape.max_y - self.sheet.max_y).max(0.0))
            .max(QUANT_FLOOR)
        } else {
            0.0
        };
        loss += res.colliding_layout_idxs.len() as f64 * QUANT_FLOOR;
        Some(ScoredPlacement {
            score: 1_000_000.0 + loss + lbf_quality,
            collision_loss: loss.max(QUANT_FLOOR),
            is_clear: false,
            placement,
        })
    }
}

fn point_on_segment(p: Point, a: Point, b: Point) -> bool {
    let cross = (p.y - a.y) * (b.x - a.x) - (p.x - a.x) * (b.y - a.y);
    if cross.abs() > 1e-7 {
        return false;
    }
    let dot = (p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y);
    if dot < -1e-7 {
        return false;
    }
    let len2 = (b.x - a.x).powi(2) + (b.y - a.y).powi(2);
    dot <= len2 + 1e-7
}

fn point_inside_or_on_poly(p: Point, poly: &[Point]) -> bool {
    if poly.len() < 3 {
        return false;
    }
    let mut inside = false;
    let mut j = poly.len() - 1;
    for i in 0..poly.len() {
        let a = poly[i];
        let b = poly[j];
        if point_on_segment(p, a, b) {
            return true;
        }
        let crosses = (a.y > p.y) != (b.y > p.y);
        if crosses {
            let x_intersect = (b.x - a.x) * (p.y - a.y)
                / ((b.y - a.y).abs().max(1e-12) * (b.y - a.y).signum())
                + a.x;
            if p.x < x_intersect {
                inside = !inside;
            }
        }
        j = i;
    }
    inside
}
