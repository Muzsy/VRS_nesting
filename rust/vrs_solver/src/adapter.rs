use crate::io::{Metrics, Placement, SolverInput, SolverOutput, Unplaced};
use crate::item::{can_fit_any_stock, expand_instances, part_has_holes};
use crate::optimizer::{try_place_on_sheet, SheetCursor};
use crate::sheet::expand_sheets;

const PROFILE_PHASE1: &str = "jagua_optimizer_phase1_outer_only";

pub fn solve(input: SolverInput) -> Result<SolverOutput, String> {
    if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        for part in &input.parts {
            if part_has_holes(part) {
                return Ok(SolverOutput {
                    contract_version: "v1".to_string(),
                    status: "unsupported".to_string(),
                    unsupported_reason: Some("UNSUPPORTED_PART_HOLES_PHASE1".to_string()),
                    placements: vec![],
                    unplaced: vec![],
                    metrics: Metrics {
                        placed_count: 0,
                        unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
                        sheet_count_used: 0,
                        seed: input.seed,
                        time_limit_s: input.time_limit_s,
                        project_name: input.project_name.clone(),
                    },
                });
            }
        }
    }

    let sheets = expand_sheets(&input.stocks)?;
    let instances = expand_instances(&input.parts)?;
    let mut placements: Vec<Placement> = Vec::new();
    let mut unplaced: Vec<Unplaced> = Vec::new();

    let mut per_sheet_cursor: Vec<SheetCursor> = sheets
        .iter()
        .map(|_| SheetCursor {
            x: 0.0,
            y: 0.0,
            row_h: 0.0,
        })
        .collect();

    for instance in &instances {
        let part = input
            .parts
            .iter()
            .find(|p| p.id == instance.part_id)
            .ok_or_else(|| format!("internal error: part not found: {}", instance.part_id))?;

        if !can_fit_any_stock(part, &sheets)? {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
            continue;
        }

        let mut placed = None;
        for (idx, sheet) in sheets.iter().enumerate() {
            if let Some(candidate) =
                try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx)
            {
                placed = Some(candidate);
                break;
            }
        }

        if let Some(p) = placed {
            placements.push(p);
        } else {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "NO_CAPACITY".to_string(),
            });
        }
    }

    let status = if unplaced.is_empty() { "ok" } else { "partial" }.to_string();
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    let placed_count = placements.len();
    let unplaced_count = unplaced.len();

    Ok(SolverOutput {
        contract_version: "v1".to_string(),
        status,
        unsupported_reason: None,
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count,
            sheet_count_used,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name,
        },
    })
}
