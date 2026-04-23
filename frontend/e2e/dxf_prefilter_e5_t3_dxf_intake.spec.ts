import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const MOCK_DXF = Buffer.from("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n", "utf-8");

const ACCEPTED_SUMMARY = {
  preflight_run_id: "pf-run-acc-1",
  run_seq: 1,
  run_status: "preflight_complete",
  acceptance_outcome: "accepted_for_import",
  finished_at: "2026-02-19T10:00:00Z",
  blocking_issue_count: 0,
  review_required_issue_count: 0,
  warning_issue_count: 1,
  total_issue_count: 1,
  applied_gap_repair_count: 2,
  applied_duplicate_dedupe_count: 0,
  total_repair_count: 2,
  recommended_action: "ready_for_next_step",
};

const ACCEPTED_DIAGNOSTICS = {
  source_inventory_summary: {
    found_layers: ["CUT", "MARK"],
    found_colors: [1, 3],
    found_linetypes: ["Continuous"],
    entity_count: 42,
    contour_count: 10,
    open_path_layer_count: 0,
    open_path_total_count: 0,
    duplicate_candidate_group_count: 0,
    duplicate_candidate_member_count: 0,
  },
  role_mapping_summary: {
    resolved_role_inventory: { cut: 8, mark: 2 },
    layer_role_assignments: [
      { layer: "CUT", role: "cut" },
      { layer: "MARK", role: "mark" },
    ],
    review_required_count: 0,
    blocking_conflict_count: 0,
  },
  issue_summary: {
    counts_by_severity: { blocking: 0, review_required: 0, warning: 1, info: 0 },
    normalized_issues: [
      { severity: "warning", family: "geometry", code: "W001", message: "Minor gap detected", source: "gap_repair" },
    ],
  },
  repair_summary: {
    counts: {
      applied_gap_repair_count: 2,
      applied_duplicate_dedupe_count: 0,
      skipped_source_entity_count: 0,
      remaining_open_path_count: 0,
      remaining_duplicate_count: 0,
      remaining_review_required_signal_count: 0,
    },
    applied_gap_repairs: [{ gap_id: "g1" }, { gap_id: "g2" }],
    applied_duplicate_dedupes: [],
    skipped_source_entities: [],
    remaining_review_required_signals: [],
  },
  acceptance_summary: {
    acceptance_outcome: "accepted_for_import",
    precedence_rule_applied: "auto_accept_if_no_blocking",
    importer_probe: { is_pass: true, error_code: null },
    validator_probe: { status: "ok", is_pass: true },
    blocking_reason_count: 0,
    review_required_reason_count: 0,
  },
  artifact_references: [
    { artifact_kind: "normalized_dxf", download_label: "Normalized DXF", path: "artifacts/normalized.dxf", exists: true },
  ],
};

const REVIEW_REQUIRED_SUMMARY = {
  preflight_run_id: "pf-run-rev-1",
  run_seq: 1,
  run_status: "preflight_complete",
  acceptance_outcome: "preflight_review_required",
  finished_at: "2026-02-19T11:00:00Z",
  blocking_issue_count: 0,
  review_required_issue_count: 2,
  warning_issue_count: 0,
  total_issue_count: 2,
  applied_gap_repair_count: 0,
  applied_duplicate_dedupe_count: 0,
  total_repair_count: 0,
  recommended_action: "review_required_wait_for_diagnostics",
};

const REVIEW_REQUIRED_DIAGNOSTICS = {
  source_inventory_summary: {
    found_layers: ["0"],
    found_colors: [7],
    found_linetypes: ["Continuous"],
    entity_count: 12,
    contour_count: 5,
    open_path_layer_count: 1,
    open_path_total_count: 3,
    duplicate_candidate_group_count: 0,
    duplicate_candidate_member_count: 0,
  },
  role_mapping_summary: {
    resolved_role_inventory: {},
    layer_role_assignments: [],
    review_required_count: 2,
    blocking_conflict_count: 0,
  },
  issue_summary: {
    counts_by_severity: { blocking: 0, review_required: 2, warning: 0, info: 0 },
    normalized_issues: [
      { severity: "review_required", family: "role_mapping", code: "R001", message: "Layer role ambiguous", source: "role_resolver" },
    ],
  },
  repair_summary: {
    counts: {
      applied_gap_repair_count: 0,
      applied_duplicate_dedupe_count: 0,
      skipped_source_entity_count: 0,
      remaining_open_path_count: 3,
      remaining_duplicate_count: 0,
      remaining_review_required_signal_count: 2,
    },
    applied_gap_repairs: [],
    applied_duplicate_dedupes: [],
    skipped_source_entities: [],
    remaining_review_required_signals: [{ signal: "ambiguous_role" }],
  },
  acceptance_summary: {
    acceptance_outcome: "preflight_review_required",
    precedence_rule_applied: "review_required_if_any_review_signal",
    importer_probe: { is_pass: false, error_code: "role_ambiguous" },
    validator_probe: { status: "review", is_pass: false },
    blocking_reason_count: 0,
    review_required_reason_count: 2,
  },
  artifact_references: [],
};

test.describe("DXF Prefilter E5-T3 — DXF Intake UI smoke / integration", () => {
  test("E5-T3 UI#1: settings panel -> upload finalize bridge captures rules_profile_snapshot_jsonb", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("p-intake-settings", "Intake Settings Bridge Test"));
    mock.state.filesByProject["p-intake-settings"] = [];
    mock.state.runsByProject["p-intake-settings"] = [];

    await page.goto("/projects/p-intake-settings/dxf-intake");
    await expect(page.getByRole("heading", { name: "Source DXF upload" })).toBeVisible();

    // Enable strict_mode (first checkbox, default false)
    await page.locator('input[type="checkbox"]').first().check();

    // Set max_gap_close_mm to 2.5 (step="0.01" distinguishes it from duplicate_contour input)
    await page.locator('input[step="0.01"]').fill("2.5");

    // Upload a source DXF via the hidden file input
    await page.locator('input[type="file"]').setInputFiles([
      { name: "source_part.dxf", mimeType: "application/dxf", buffer: MOCK_DXF },
    ]);

    await expect(page.getByText("Upload complete. Preflight starts automatically.")).toBeVisible();

    // File row appears in the latest preflight runs table after loadData()
    await expect(page.getByText("source_part.dxf")).toBeVisible();

    // Assert finalize body was captured with correct rules_profile_snapshot_jsonb
    expect(mock.state.finalizedBodies).toHaveLength(1);
    const body = mock.state.finalizedBodies[0];
    const snapshot = body.rules_profile_snapshot_jsonb as Record<string, unknown>;
    expect(snapshot).toBeDefined();
    expect(snapshot.strict_mode).toBe(true);
    expect(snapshot.max_gap_close_mm).toBe(2.5);
    expect(snapshot.auto_repair_enabled).toBe(false);
    expect(snapshot.interactive_review_on_ambiguity).toBe(true);
  });

  test("E5-T3 UI#2: accepted latest run -> acceptance badge + diagnostics drawer with all blocks", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("p-intake-accepted", "Accepted Preflight Project"));
    mock.state.filesByProject["p-intake-accepted"] = [
      {
        id: "file-accepted-1",
        project_id: "p-intake-accepted",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "part_accepted.dxf",
        storage_key: "users/e2e-user/projects/p-intake-accepted/files/file-accepted-1/part_accepted.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-02-19T00:00:00Z",
        latest_preflight_summary: ACCEPTED_SUMMARY,
        latest_preflight_diagnostics: ACCEPTED_DIAGNOSTICS,
      },
    ];
    mock.state.runsByProject["p-intake-accepted"] = [];

    await page.goto("/projects/p-intake-accepted/dxf-intake");
    await expect(page.getByRole("heading", { name: "Latest preflight runs" })).toBeVisible();

    // Acceptance badge shows "accepted" (accepted_for_import outcome) — exact to avoid substring matches
    await expect(page.getByText("accepted", { exact: true })).toBeVisible();

    // Recommended action is advisory: "Ready for next step" (not a mutating button)
    await expect(page.getByText("Ready for next step")).toBeVisible();

    // "View diagnostics" button enabled and opens drawer
    await page.getByRole("button", { name: "View diagnostics" }).click();

    // Drawer header
    await expect(page.getByRole("heading", { name: "Diagnostics" })).toBeVisible();

    // All 6 diagnostic blocks must render
    await expect(page.getByRole("heading", { name: "Source inventory" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Role mapping" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Issues" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Repairs" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Acceptance" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Artifacts" })).toBeVisible();

    // Drawer is read-only: only a Close button, no mutation actions
    await expect(page.getByRole("button", { name: "Close" })).toBeVisible();

    // Close drawer
    await page.getByRole("button", { name: "Close" }).click();
    await expect(page.getByRole("heading", { name: "Diagnostics" })).not.toBeVisible();
  });

  test("E5-T3 UI#3: non-accepted (review_required) latest run -> correct badge, no false accepted advisory", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("p-intake-review", "Review Required Project"));
    mock.state.filesByProject["p-intake-review"] = [
      {
        id: "file-review-1",
        project_id: "p-intake-review",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "part_review_required.dxf",
        storage_key: "users/e2e-user/projects/p-intake-review/files/file-review-1/part_review_required.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-02-19T00:00:00Z",
        latest_preflight_summary: REVIEW_REQUIRED_SUMMARY,
        latest_preflight_diagnostics: REVIEW_REQUIRED_DIAGNOSTICS,
      },
    ];
    mock.state.runsByProject["p-intake-review"] = [];

    await page.goto("/projects/p-intake-review/dxf-intake");
    await expect(page.getByRole("heading", { name: "Latest preflight runs" })).toBeVisible();

    // Correct non-accepted badge — exact to avoid substring match with project name
    await expect(page.getByText("review required", { exact: true })).toBeVisible();

    // Recommended action for non-accepted state
    await expect(page.getByText("Wait for diagnostics")).toBeVisible();

    // "Ready for next step" must NOT appear (no false accepted advisory)
    await expect(page.getByText("Ready for next step")).not.toBeVisible();

    // Diagnostics drawer is accessible since diagnostics payload exists
    const viewBtn = page.getByRole("button", { name: "View diagnostics" });
    await expect(viewBtn).toBeEnabled();
    await viewBtn.click();
    await expect(page.getByRole("heading", { name: "Diagnostics" })).toBeVisible();

    // Drawer acceptance badge also reflects non-accepted state
    await expect(page.locator(".fixed").getByText("review required", { exact: true })).toBeVisible();
  });
});
