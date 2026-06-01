use super::*;

pub struct UniformBBoxSampler<'a> {
    sheet: &'a SheetShape,
    inst: &'a SPInstance,
}

impl<'a> UniformBBoxSampler<'a> {
    pub fn new(sheet: &'a SheetShape, inst: &'a SPInstance) -> Self {
        Self { sheet, inst }
    }

    pub fn samples_for(
        &self,
        rot: f64,
        grid_n: usize,
        rng: &mut DeterministicRng,
    ) -> Vec<(f64, f64)> {
        let (rw, rh) = dims_for_rotation(self.inst.part.width, self.inst.part.height, rot);
        if rw > self.sheet.width + 1e-9 || rh > self.sheet.height + 1e-9 {
            return Vec::new();
        }
        let max_x = (self.sheet.max_x - rw).max(self.sheet.min_x);
        let max_y = (self.sheet.max_y - rh).max(self.sheet.min_y);
        let mut out = vec![
            (self.sheet.min_x, self.sheet.min_y),
            (max_x, self.sheet.min_y),
            (self.sheet.min_x, max_y),
        ];
        let n = grid_n.max(1);
        let step_x = (max_x - self.sheet.min_x) / (n as f64 + 1.0);
        let step_y = (max_y - self.sheet.min_y) / (n as f64 + 1.0);
        for gy in 1..=n {
            for gx in 1..=n {
                out.push((
                    self.sheet.min_x + step_x * gx as f64,
                    self.sheet.min_y + step_y * gy as f64,
                ));
            }
        }
        for _ in 0..n {
            out.push((
                self.sheet.min_x + rng.next_f64() * (max_x - self.sheet.min_x).max(0.0),
                self.sheet.min_y + rng.next_f64() * (max_y - self.sheet.min_y).max(0.0),
            ));
        }
        out
    }
}
