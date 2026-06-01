use super::*;

// ---------------------------------------------------------------------------
// instance + problem
// ---------------------------------------------------------------------------

/// A native expanded item instance (replaces lookups through `crate::io::Placement`).
#[derive(Debug, Clone)]
pub struct SPInstance {
    pub idx: usize,
    pub instance_id: String,
    pub part_id: String,
    pub part: Part,
    pub allowed_rotations_deg: Vec<f64>,
    /// True when the rotation policy permits continuous/free rotation, enabling
    /// the coordinate-descent rotation-wiggle axis. Orthogonal/discrete fixtures
    /// leave this false and keep their fixed rotation set.
    pub continuous_rotation: bool,
}

/// Native fixed-sheet container set.
#[derive(Debug, Clone)]
pub struct SparrowContainer {
    pub sheets: Vec<SheetShape>,
}

/// Native rotation domain (resolved per instance).
#[derive(Debug, Clone)]
pub struct SparrowRotationDomain {
    pub allowed_rotations_deg: Vec<f64>,
}

/// Native Sparrow problem — the single conversion from VRS input structures.
pub struct SparrowProblem {
    pub instances: Vec<SPInstance>,
    pub container: SparrowContainer,
    pub config: SparrowConfig,
    /// Never-fit instances retained for output projection (no silent drops).
    pub pre_unplaced: Vec<Unplaced>,
}

impl SparrowProblem {
    /// One-way I/O conversion: VRS parts/sheets/policy -> native problem.
    pub fn from_solver_input(
        parts: &[Part],
        sheets: &[SheetShape],
        rotation_context: &RotationResolveContext,
        extra_unplaced: Vec<Unplaced>,
        config: SparrowConfig,
    ) -> Result<Self, String> {
        let expanded: Vec<Instance> = expand_instances_with_policy(parts, rotation_context)?;
        let mut instances: Vec<SPInstance> = Vec::new();
        let mut pre_unplaced: Vec<Unplaced> = extra_unplaced;
        for inst in expanded {
            let part = parts.iter().find(|p| p.id == inst.part_id).ok_or_else(|| {
                format!(
                    "part {} missing for instance {}",
                    inst.part_id, inst.instance_id
                )
            })?;
            if !can_fit_any_stock_with_policy(part, sheets, rotation_context)? {
                pre_unplaced.push(Unplaced {
                    instance_id: inst.instance_id.clone(),
                    part_id: inst.part_id.clone(),
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
                continue;
            }
            let continuous_rotation = match part.rotation_policy {
                Some(RotationPolicyKind::Continuous) => true,
                Some(_) => false,
                None => matches!(
                    rotation_context.global_policy,
                    Some(RotationPolicyKind::Continuous)
                ),
            };
            let idx = instances.len();
            instances.push(SPInstance {
                idx,
                instance_id: inst.instance_id,
                part_id: inst.part_id,
                part: part.clone(),
                allowed_rotations_deg: inst.allowed_rotations_deg,
                continuous_rotation,
            });
        }
        Ok(Self {
            instances,
            container: SparrowContainer {
                sheets: sheets.to_vec(),
            },
            config,
            pre_unplaced,
        })
    }

    pub fn rotation_domain(&self, idx: usize) -> SparrowRotationDomain {
        SparrowRotationDomain {
            allowed_rotations_deg: self.instances[idx].allowed_rotations_deg.clone(),
        }
    }
}

// ---------------------------------------------------------------------------
// layout
// ---------------------------------------------------------------------------

/// Native placement record (NOT `crate::io::Placement`). Indexed by `SPInstance`.
#[derive(Debug, Clone)]
pub struct SparrowPlacement {
    pub instance_idx: usize,
    pub sheet_index: usize,
    /// Anchor coordinates (consistent with `placement_anchor_from_rect_min`).
    pub x: f64,
    pub y: f64,
    pub rotation_deg: f64,
}

/// Native layout: one placement per (placed) instance, keyed by instance index.
#[derive(Debug, Clone)]
pub struct SparrowLayout {
    pub placements: Vec<SparrowPlacement>,
}

impl SparrowLayout {
    pub fn snapshot(&self) -> SparrowLayout {
        self.clone()
    }
    pub fn len(&self) -> usize {
        self.placements.len()
    }
    pub fn is_empty(&self) -> bool {
        self.placements.is_empty()
    }
    /// Iterate (layout index) of items on `sheet_idx`.
    pub fn items_on_sheet(&self, sheet_idx: usize) -> Vec<usize> {
        (0..self.placements.len())
            .filter(|&i| self.placements[i].sheet_index == sheet_idx)
            .collect()
    }
}

pub struct SparrowSolution {
    pub layout: SparrowLayout,
    pub feasible: bool,
}

impl SparrowSolution {
    /// Project the native solution to VRS output placements (output boundary only).
    pub fn to_solver_projection(&self, instances: &[SPInstance]) -> Vec<Placement> {
        self.layout
            .placements
            .iter()
            .map(|p| {
                let inst = &instances[p.instance_idx];
                Placement {
                    instance_id: inst.instance_id.clone(),
                    part_id: inst.part_id.clone(),
                    sheet_index: p.sheet_index,
                    x: p.x,
                    y: p.y,
                    rotation_deg: p.rotation_deg,
                }
            })
            .collect()
    }
}

pub struct SparrowSolveResult {
    pub solution: SparrowSolution,
    /// Projected output placements (VRS boundary).
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub feasible: bool,
    pub diagnostics: SparrowDiagnostics,
}
