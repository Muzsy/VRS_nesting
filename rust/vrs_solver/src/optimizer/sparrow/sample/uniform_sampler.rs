use super::*;

/// Number of rotations sampled for a continuous-rotation item (upstream
/// `ROT_N_SAMPLES = 16`).
pub(crate) const ROT_N_SAMPLES: usize = 16;

/// Upstream `UniformBBoxSampler` (`.cache/sparrow/src/sample/uniform_sampler.rs`),
/// adapted to fixed sheets.
///
/// For each candidate rotation it precomputes the valid rect-min translation
/// range so the rotated shape stays inside the sheet, intersected with the
/// requested sample bbox (focused or container-wide). `sample` then draws a
/// random rotation entry and a random rect-min within its ranges — random
/// sampling is the primary algorithm, not grid enumeration.
#[derive(Clone, Debug)]
pub struct UniformBBoxSampler {
    rot_entries: Vec<RotEntry>,
}

#[derive(Clone, Debug)]
struct RotEntry {
    rot: f64,
    x_range: (f64, f64),
    y_range: (f64, f64),
}

impl UniformBBoxSampler {
    /// Build a sampler for `inst` whose rect-min samples stay inside `sheet` and
    /// within `sample_bbox` = `(min_x, min_y, max_x, max_y)`. Supports none /
    /// discrete / continuous rotation policies. Returns `None` if no rotation has
    /// a non-empty valid range (the item cannot be placed within the bbox).
    pub fn new(
        sample_bbox: (f64, f64, f64, f64),
        inst: &SPInstance,
        sheet: &SheetShape,
    ) -> Option<Self> {
        let rotations: Vec<f64> = Self::rotations_for(inst);
        let (sb_min_x, sb_min_y, sb_max_x, sb_max_y) = sample_bbox;

        let rot_entries: Vec<RotEntry> = rotations
            .into_iter()
            .filter_map(|rot| {
                let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
                // Valid rect-min range so the rotated shape stays inside the sheet.
                let cont_x = (sheet.min_x, sheet.max_x - rw);
                let cont_y = (sheet.min_y, sheet.max_y - rh);
                // Intersect with the requested sample bbox.
                let x_range = intersect_range(cont_x, (sb_min_x, sb_max_x));
                let y_range = intersect_range(cont_y, (sb_min_y, sb_max_y));
                if range_is_empty(x_range) || range_is_empty(y_range) {
                    None
                } else {
                    Some(RotEntry {
                        rot,
                        x_range,
                        y_range,
                    })
                }
            })
            .collect();

        if rot_entries.is_empty() {
            None
        } else {
            Some(Self { rot_entries })
        }
    }

    /// Rotation candidates for the item: none → [0], discrete → allowed set,
    /// continuous → `ROT_N_SAMPLES` evenly spaced rotations over a full turn.
    fn rotations_for(inst: &SPInstance) -> Vec<f64> {
        if inst.continuous_rotation {
            (0..ROT_N_SAMPLES)
                .map(|i| i as f64 * 360.0 / ROT_N_SAMPLES as f64)
                .collect()
        } else if inst.allowed_rotations_deg.is_empty() {
            vec![0.0]
        } else {
            inst.allowed_rotations_deg.clone()
        }
    }

    /// Draw a random `(rect_min_x, rect_min_y, rotation_deg)` sample: pick a random
    /// rotation entry, then a uniform random rect-min within its valid ranges.
    pub fn sample(&self, rng: &mut DeterministicRng) -> (f64, f64, f64) {
        let idx = (rng.next_u64() as usize) % self.rot_entries.len();
        let e = &self.rot_entries[idx];
        let rmx = random_in_range(rng, e.x_range);
        let rmy = random_in_range(rng, e.y_range);
        (rmx, rmy, e.rot)
    }
}

/// Uniform random value within an inclusive `[lo, hi]` range.
fn random_in_range(rng: &mut DeterministicRng, range: (f64, f64)) -> f64 {
    range.0 + rng.next_f64() * (range.1 - range.0).max(0.0)
}

fn intersect_range(a: (f64, f64), b: (f64, f64)) -> (f64, f64) {
    (a.0.max(b.0), a.1.min(b.1))
}

fn range_is_empty(r: (f64, f64)) -> bool {
    r.0 > r.1 + 1e-9
}
