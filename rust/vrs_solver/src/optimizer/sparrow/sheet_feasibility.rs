//! SGH-Q58A: `SheetFeasibilityHints` — preprocessing-level strategic feasibility for a whole job.
//!
//! Estimates sheet distribution and critical-part quotas BEFORE placement. It does not replace exact
//! nesting and does not change any placement decision (Q58B consumes it). Every estimate is labelled
//! with a confidence + basis and a status (`unknown`/`plausible`/`unlikely`/`proven`/`rejected`) — the
//! area lower bound is never treated as a final sheet-count proof.

use super::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CapacityStatus {
    Unknown,
    Plausible,
    Unlikely,
    ProvenByFocusedTest,
    RejectedByFocusedTest,
}

impl CapacityStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            CapacityStatus::Unknown => "unknown",
            CapacityStatus::Plausible => "plausible",
            CapacityStatus::Unlikely => "unlikely",
            CapacityStatus::ProvenByFocusedTest => "proven_by_focused_test",
            CapacityStatus::RejectedByFocusedTest => "rejected_by_focused_test",
        }
    }
}

#[derive(Debug, Clone)]
pub struct CriticalPartTypeSheetHint {
    pub part_id: String,
    pub quantity: usize,
    pub criticality_tier: &'static str,
    pub estimated_max_per_sheet: usize,
    pub target_per_sheet: usize,
    pub target_distribution: Vec<usize>,
    pub status: CapacityStatus,
    pub confidence: f64,
    pub basis: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct RepeatedFamilySheetHint {
    pub family_key: String,
    pub member_part_ids: Vec<String>,
    pub total_quantity: usize,
    pub suggests_grid_or_band: bool,
}

#[derive(Debug, Clone)]
pub struct DangerPartHint {
    pub part_id: String,
    pub fit_difficulty_score: f64,
    pub sheet_span_risk_score: f64,
    pub orientation_candidate_count: usize,
    pub reasons: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct TargetSheetStrategyHint {
    pub area_lower_bound: usize,
    pub strategy: String,
}

#[derive(Debug, Clone, Default)]
pub struct SheetFeasibilityDiagnostics {
    pub usable_sheet_area_basis: String,
    pub total_part_area: f64,
    pub usable_sheet_area: f64,
}

#[derive(Debug, Clone)]
pub struct SheetFeasibilityHints {
    pub sheet_width: f64,
    pub sheet_height: f64,
    pub margin_mm: f64,
    pub spacing_mm: f64,
    pub sheet_count_area_lower_bound: usize,
    pub total_area_ratio: f64,
    pub critical_part_type_hints: Vec<CriticalPartTypeSheetHint>,
    pub repeated_family_hints: Vec<RepeatedFamilySheetHint>,
    pub danger_parts: Vec<DangerPartHint>,
    pub target_sheet_strategy: TargetSheetStrategyHint,
    pub diagnostics: SheetFeasibilityDiagnostics,
}

impl SheetFeasibilityHints {
    pub fn to_diagnostics_json(&self) -> serde_json::Value {
        let crit: Vec<serde_json::Value> = self
            .critical_part_type_hints
            .iter()
            .map(|c| {
                serde_json::json!({
                    "part_id": c.part_id,
                    "quantity": c.quantity,
                    "criticality_tier": c.criticality_tier,
                    "estimated_max_per_sheet": c.estimated_max_per_sheet,
                    "target_per_sheet": c.target_per_sheet,
                    "target_distribution": c.target_distribution,
                    "status": c.status.as_str(),
                    "confidence": round4(c.confidence),
                    "basis": c.basis,
                })
            })
            .collect();
        let fams: Vec<serde_json::Value> = self
            .repeated_family_hints
            .iter()
            .map(|f| {
                serde_json::json!({
                    "family_key": f.family_key,
                    "member_part_ids": f.member_part_ids,
                    "total_quantity": f.total_quantity,
                    "suggests_grid_or_band": f.suggests_grid_or_band,
                })
            })
            .collect();
        let danger: Vec<serde_json::Value> = self
            .danger_parts
            .iter()
            .map(|d| {
                serde_json::json!({
                    "part_id": d.part_id,
                    "fit_difficulty_score": round4(d.fit_difficulty_score),
                    "sheet_span_risk_score": round4(d.sheet_span_risk_score),
                    "orientation_candidate_count": d.orientation_candidate_count,
                    "reasons": d.reasons,
                })
            })
            .collect();
        serde_json::json!({
            "sheet_width": self.sheet_width,
            "sheet_height": self.sheet_height,
            "margin": self.margin_mm,
            "spacing": self.spacing_mm,
            "usable_sheet_area_basis": self.diagnostics.usable_sheet_area_basis,
            "usable_sheet_area": round4(self.diagnostics.usable_sheet_area),
            "total_part_area": round4(self.diagnostics.total_part_area),
            "total_area_ratio": round4(self.total_area_ratio),
            "area_lower_bound": self.sheet_count_area_lower_bound,
            "critical_part_type_count": self.critical_part_type_hints.len(),
            "repeated_family_count": self.repeated_family_hints.len(),
            "danger_part_count": self.danger_parts.len(),
            "target_sheet_strategy": {
                "area_lower_bound": self.target_sheet_strategy.area_lower_bound,
                "strategy": self.target_sheet_strategy.strategy,
            },
            "critical_hints": crit,
            "repeated_family_hints": fams,
            "danger_parts": danger,
        })
    }
}

/// Build the job-level feasibility hints for `parts` on a sheet. Deterministic; placement-free.
pub fn build_sheet_feasibility_hints(
    parts: &[Part],
    sheet_width: f64,
    sheet_height: f64,
    margin_mm: f64,
    spacing_mm: f64,
) -> Result<SheetFeasibilityHints, String> {
    let rotation_context =
        RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let raw_stock = crate::sheet::Stock {
        id: "S_FEAS".to_string(),
        quantity: parts.len().max(1) as i64,
        width: Some(sheet_width),
        height: Some(sheet_height),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let raw_sheet = crate::sheet::stock_to_shape(&raw_stock)?;
    let cfg = SparrowConfig::from_solver_input(
        1.0,
        CollisionBackendKind::Cde,
        rotation_context.clone(),
        42,
    )
    .with_spacing_mm(spacing_mm);
    let problem = SparrowProblem::from_solver_input(
        parts,
        std::slice::from_ref(&raw_sheet),
        &rotation_context,
        Vec::new(),
        cfg,
    )?;

    let usable_w = (sheet_width - 2.0 * margin_mm).max(1.0);
    let usable_h = (sheet_height - 2.0 * margin_mm).max(1.0);
    let usable_area = usable_w * usable_h;
    let usable_long = usable_w.max(usable_h);

    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut total_part_area = 0.0_f64;
    let mut critical_hints: Vec<CriticalPartTypeSheetHint> = Vec::new();
    let mut danger_parts: Vec<DangerPartHint> = Vec::new();
    let mut family_acc: std::collections::HashMap<String, (Vec<String>, usize)> =
        std::collections::HashMap::new();

    for inst in &problem.instances {
        let sp = inst.shape_profile.as_ref();
        let pa = inst.part_analysis.as_ref();
        // total area accumulates per-instance (full demand).
        total_part_area += sp.true_area;
        if !seen.insert(inst.part_id.clone()) {
            continue;
        }
        // Repeated family accumulation.
        if !pa.family_key.is_empty() {
            let e = family_acc.entry(pa.family_key.clone()).or_default();
            e.0.push(inst.part_id.clone());
            e.1 += sp.quantity;
        }

        if sp.is_critical() {
            // Min footprint bbox area across the orientation-catalog extrema (tightest packing frame).
            let min_bbox_area = inst
                .orientation_catalog
                .extrema_samples
                .iter()
                .map(|s| (s.width * s.height).max(1.0))
                .fold(f64::MAX, f64::min);
            let min_bbox_area = if min_bbox_area.is_finite() {
                min_bbox_area
            } else {
                sp.bbox_area
            };
            // Narrowest extent across samples → span-based strip cap.
            let min_extent = inst
                .orientation_catalog
                .extrema_samples
                .iter()
                .map(|s| s.width.min(s.height))
                .fold(f64::MAX, f64::min);
            let min_extent = if min_extent.is_finite() && min_extent > 0.0 {
                min_extent
            } else {
                sp.min_dim.max(1.0)
            };

            let area_cap = (usable_area / min_bbox_area).floor().max(0.0) as usize;
            let span_cap = (usable_long / min_extent).floor().max(0.0) as usize;
            let estimated_max_per_sheet = area_cap.min(span_cap.max(1));
            let target_per_sheet = estimated_max_per_sheet.min(sp.quantity).max(0);
            let target_distribution = distribute(sp.quantity, target_per_sheet);

            // Conservative status: area allows it (plausible) but never claim proof here.
            let status = if estimated_max_per_sheet == 0 {
                CapacityStatus::Unlikely
            } else if pa.fit_difficulty.score >= 0.6 {
                // High fit difficulty: area may allow it but packing is risky.
                CapacityStatus::Unknown
            } else {
                CapacityStatus::Plausible
            };
            let confidence = (0.4 + 0.4 * (1.0 - pa.fit_difficulty.score)).clamp(0.0, 0.85);
            let basis = vec![
                format!("area_cap={area_cap}"),
                format!("span_cap={span_cap}"),
                format!("min_bbox_area={:.0}", min_bbox_area),
                format!("fit_difficulty={:.3}", pa.fit_difficulty.score),
            ];
            critical_hints.push(CriticalPartTypeSheetHint {
                part_id: inst.part_id.clone(),
                quantity: sp.quantity,
                criticality_tier: pa.diagnostics.criticality_tier,
                estimated_max_per_sheet,
                target_per_sheet,
                target_distribution,
                status,
                confidence,
                basis,
            });

            // Danger part detection.
            let mut reasons: Vec<String> = Vec::new();
            if sp.bbox_sheet_span_ratio >= 0.5 {
                reasons.push("large_sheet_span".to_string());
            }
            if pa.fit_difficulty.score >= 0.5 {
                reasons.push("high_fit_difficulty".to_string());
            }
            if inst.orientation_catalog.diagnostics.candidate_count <= 2 {
                reasons.push("few_useful_orientations".to_string());
            }
            if sp.quantity >= 4 {
                reasons.push("large_repeated_quantity".to_string());
            }
            if !reasons.is_empty() {
                danger_parts.push(DangerPartHint {
                    part_id: inst.part_id.clone(),
                    fit_difficulty_score: pa.fit_difficulty.score,
                    sheet_span_risk_score: pa.sheet_span_risk_score,
                    orientation_candidate_count: inst
                        .orientation_catalog
                        .diagnostics
                        .candidate_count,
                    reasons,
                });
            }
        }
    }

    let area_lower_bound = (total_part_area / usable_area).ceil().max(1.0) as usize;
    let total_area_ratio = total_part_area / usable_area;

    let repeated_family_hints: Vec<RepeatedFamilySheetHint> = {
        let mut v: Vec<RepeatedFamilySheetHint> = family_acc
            .into_iter()
            .filter(|(_, (_, qty))| *qty >= 4)
            .map(|(fk, (ids, qty))| RepeatedFamilySheetHint {
                family_key: fk,
                member_part_ids: ids,
                total_quantity: qty,
                suggests_grid_or_band: qty >= 4,
            })
            .collect();
        v.sort_by(|a, b| {
            b.total_quantity
                .cmp(&a.total_quantity)
                .then_with(|| a.family_key.cmp(&b.family_key))
        });
        v
    };

    critical_hints.sort_by(|a, b| {
        b.quantity
            .cmp(&a.quantity)
            .then_with(|| a.part_id.cmp(&b.part_id))
    });
    danger_parts.sort_by(|a, b| {
        b.fit_difficulty_score
            .partial_cmp(&a.fit_difficulty_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.part_id.cmp(&b.part_id))
    });

    let strategy = if area_lower_bound <= 1 {
        "single_sheet_plausible".to_string()
    } else {
        format!("at_least_{area_lower_bound}_sheets_by_area")
    };

    Ok(SheetFeasibilityHints {
        sheet_width,
        sheet_height,
        margin_mm,
        spacing_mm,
        sheet_count_area_lower_bound: area_lower_bound,
        total_area_ratio,
        critical_part_type_hints: critical_hints,
        repeated_family_hints,
        danger_parts,
        target_sheet_strategy: TargetSheetStrategyHint {
            area_lower_bound,
            strategy,
        },
        diagnostics: SheetFeasibilityDiagnostics {
            usable_sheet_area_basis: "margin_shrunk".to_string(),
            total_part_area,
            usable_sheet_area: usable_area,
        },
    })
}

/// Distribute `quantity` across sheets of at most `per_sheet` each (a hint, not a proof).
fn distribute(quantity: usize, per_sheet: usize) -> Vec<usize> {
    if quantity == 0 {
        return vec![];
    }
    if per_sheet == 0 {
        return vec![quantity]; // cannot place per estimate; flag the whole demand on one bucket
    }
    let mut out = Vec::new();
    let mut left = quantity;
    while left > 0 {
        let take = left.min(per_sheet);
        out.push(take);
        left -= take;
    }
    out
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rect(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![],
            rotation_policy: Some(RotationPolicyKind::Continuous),
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])),
            prepared_outer_points: None,
        }
    }

    fn hints(parts: &[Part]) -> SheetFeasibilityHints {
        build_sheet_feasibility_hints(parts, 1500.0, 3000.0, 5.0, 8.0).expect("hints")
    }

    #[test]
    fn area_lower_bound_is_deterministic_and_at_least_one() {
        let parts = vec![
            rect("big", 1200.0, 300.0, 6),
            rect("filler", 40.0, 40.0, 50),
        ];
        let a = hints(&parts);
        let b = hints(&parts);
        assert_eq!(
            a.sheet_count_area_lower_bound,
            b.sheet_count_area_lower_bound
        );
        assert!(a.sheet_count_area_lower_bound >= 1);
        assert_eq!(a.diagnostics.usable_sheet_area_basis, "margin_shrunk");
    }

    #[test]
    fn repeated_critical_type_gets_distribution_hint() {
        let parts = vec![rect("big", 1200.0, 300.0, 6)];
        let h = hints(&parts);
        let c = h
            .critical_part_type_hints
            .iter()
            .find(|c| c.part_id == "big")
            .expect("crit hint");
        assert_eq!(c.quantity, 6);
        let sum: usize = c.target_distribution.iter().sum();
        assert_eq!(sum, 6, "distribution must cover the full quantity");
    }

    #[test]
    fn danger_parts_include_large_repeated_anchor() {
        let parts = vec![rect("big", 1200.0, 300.0, 6)];
        let h = hints(&parts);
        assert!(
            h.danger_parts.iter().any(|d| d.part_id == "big"),
            "a large repeated critical anchor must be flagged as a danger part"
        );
    }

    #[test]
    fn estimates_are_labelled_not_proven() {
        let parts = vec![rect("big", 1200.0, 300.0, 6)];
        let h = hints(&parts);
        for c in &h.critical_part_type_hints {
            assert!(
                !matches!(c.status, CapacityStatus::ProvenByFocusedTest),
                "Q58A must not claim proof; only hint statuses"
            );
            assert!(c.confidence <= 0.85);
        }
    }
}
