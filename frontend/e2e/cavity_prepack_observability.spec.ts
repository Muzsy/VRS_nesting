import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const PROJECT_ID = "project-cavity-t7";
const RUN_ID = "run-cavity-t7";

test("T7: DXF Intake diagnostics drawer shows cavity observability block when data exists", async ({ page }) => {
  const mock = await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "Cavity Intake Project",
        description: "",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        archived_at: null,
      },
    ],
    initialFilesByProject: {
      [PROJECT_ID]: [
        {
          id: "file-cavity-1",
          project_id: PROJECT_ID,
          uploaded_by: "e2e-user",
          file_type: "source_dxf",
          original_filename: "cavity_parent.dxf",
          storage_key: "mock/cavity_parent.dxf",
          validation_status: "ok",
          validation_error: null,
          uploaded_at: "2026-01-01T00:00:00Z",
          latest_preflight_summary: {
            preflight_run_id: "pf-cavity-1",
            run_seq: 1,
            run_status: "preflight_complete",
            acceptance_outcome: "accepted_for_import",
            finished_at: "2026-01-01T00:00:05Z",
            blocking_issue_count: 0,
            review_required_issue_count: 0,
            warning_issue_count: 0,
            total_issue_count: 0,
            applied_gap_repair_count: 0,
            applied_duplicate_dedupe_count: 0,
            total_repair_count: 0,
            recommended_action: "ready_for_next_step",
            cavity_observability: {
              internal_hole_count: 2,
              has_internal_holes: true,
              usable_cavity_candidate_count: null,
              too_small_or_invalid_cavity_count: null,
              importer_probe_pass: true,
              estimation_basis: "importer_probe_hole_count_only",
            },
          },
          latest_preflight_diagnostics: {
            source_inventory_summary: {
              found_layers: ["CUT"],
              found_colors: [1],
              found_linetypes: ["Continuous"],
              entity_count: 10,
              contour_count: 2,
              open_path_layer_count: 0,
              open_path_total_count: 0,
              duplicate_candidate_group_count: 0,
              duplicate_candidate_member_count: 0,
            },
            role_mapping_summary: {
              resolved_role_inventory: { cut: 2 },
              layer_role_assignments: [{ layer: "CUT", role: "cut" }],
              review_required_count: 0,
              blocking_conflict_count: 0,
            },
            issue_summary: {
              counts_by_severity: { blocking: 0, review_required: 0, warning: 0, info: 0 },
              normalized_issues: [],
            },
            repair_summary: {
              counts: {
                applied_gap_repair_count: 0,
                applied_duplicate_dedupe_count: 0,
                skipped_source_entity_count: 0,
                remaining_open_path_count: 0,
                remaining_duplicate_count: 0,
                remaining_review_required_signal_count: 0,
              },
              applied_gap_repairs: [],
              applied_duplicate_dedupes: [],
              skipped_source_entities: [],
              remaining_review_required_signals: [],
            },
            acceptance_summary: {
              acceptance_outcome: "accepted_for_import",
              precedence_rule_applied: "auto_accept_if_no_blocking",
              importer_probe: { is_pass: true, hole_count: 2, error_code: null },
              validator_probe: { status: "ok", is_pass: true },
              blocking_reason_count: 0,
              review_required_reason_count: 0,
            },
            cavity_observability: {
              internal_hole_count: 2,
              has_internal_holes: true,
              usable_cavity_candidate_count: null,
              too_small_or_invalid_cavity_count: null,
              importer_probe_pass: true,
              estimation_basis: "importer_probe_hole_count_only",
            },
            artifact_references: [],
          },
        },
      ],
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/dxf-intake`);
  await page.getByRole("button", { name: "View diagnostics" }).click();

  await expect(page.getByRole("heading", { name: "Cavity observability" })).toBeVisible();
  await expect(page.getByText("Internal hole count: 2")).toBeVisible();
  await expect(page.getByText("Has internal holes: yes")).toBeVisible();
  await expect(page.getByText(/Basis: importer_probe_hole_count_only/)).toBeVisible();

  void mock;
});

test("T7: Run Detail shows cavity prepack summary only when viewer-data provides it", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "Cavity Run Detail Project",
        description: "",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-cavity-t7",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: "2026-01-01T00:00:00Z",
          started_at: "2026-01-01T00:00:01Z",
          finished_at: "2026-01-01T00:00:15Z",
          duration_sec: 14,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 3, unplaced_count: 0, sheet_count: 1 },
        },
      ],
    },
    initialViewerDataByRun: {
      [RUN_ID]: {
        run_id: RUN_ID,
        status: "done",
        sheet_count: 1,
        sheets: [],
        placements: [],
        unplaced: [],
        requested_engine_backend: "nesting_engine_v2",
        effective_engine_backend: "nesting_engine_v2",
        backend_resolution_source: "snapshot_solver_config",
        strategy_resolution_source: "run_config",
        cavity_prepack_summary: {
          enabled: true,
          version: "cavity_plan_v1",
          virtual_parent_count: 1,
          internal_placements_count: 2,
          quantity_reduced_part_count: 1,
          top_level_holes_removed_count: 1,
        },
      } as any,
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);
  await expect(page.getByText("Cavity prepack summary")).toBeVisible();
  await expect(page.getByText("enabled: true")).toBeVisible();
  await expect(page.getByText("version: cavity_plan_v1")).toBeVisible();
  await expect(page.getByText("internal_placements_count: 2")).toBeVisible();

  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "Cavity Run Detail Project",
        description: "",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-cavity-t7",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: "2026-01-01T00:00:00Z",
          started_at: "2026-01-01T00:00:01Z",
          finished_at: "2026-01-01T00:00:15Z",
          duration_sec: 14,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 3, unplaced_count: 0, sheet_count: 1 },
        },
      ],
    },
    initialViewerDataByRun: {
      [RUN_ID]: {
        run_id: RUN_ID,
        status: "done",
        sheet_count: 1,
        sheets: [],
        placements: [],
        unplaced: [],
        requested_engine_backend: "nesting_engine_v2",
        effective_engine_backend: "nesting_engine_v2",
        backend_resolution_source: "snapshot_solver_config",
        strategy_resolution_source: "run_config",
      },
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);
  await expect(page.getByText("Cavity prepack summary")).toHaveCount(0);
});
