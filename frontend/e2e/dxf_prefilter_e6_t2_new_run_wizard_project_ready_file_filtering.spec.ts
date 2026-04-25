import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

function acceptedSummary(runId: string): Record<string, unknown> {
  return {
    preflight_run_id: runId,
    run_seq: 1,
    run_status: "preflight_complete",
    acceptance_outcome: "accepted_for_import",
    finished_at: "2026-04-26T10:00:00Z",
    blocking_issue_count: 0,
    review_required_issue_count: 0,
    warning_issue_count: 0,
    total_issue_count: 0,
    applied_gap_repair_count: 0,
    applied_duplicate_dedupe_count: 0,
    total_repair_count: 0,
    recommended_action: "ready_for_next_step",
  };
}

function rejectedSummary(runId: string): Record<string, unknown> {
  return {
    preflight_run_id: runId,
    run_seq: 1,
    run_status: "preflight_complete",
    acceptance_outcome: "preflight_rejected",
    finished_at: "2026-04-26T10:01:00Z",
    blocking_issue_count: 2,
    review_required_issue_count: 0,
    warning_issue_count: 0,
    total_issue_count: 2,
    applied_gap_repair_count: 0,
    applied_duplicate_dedupe_count: 0,
    total_repair_count: 0,
    recommended_action: "rejected_fix_and_reupload",
  };
}

function reviewSummary(runId: string): Record<string, unknown> {
  return {
    preflight_run_id: runId,
    run_seq: 1,
    run_status: "preflight_complete",
    acceptance_outcome: "preflight_review_required",
    finished_at: "2026-04-26T10:02:00Z",
    blocking_issue_count: 0,
    review_required_issue_count: 1,
    warning_issue_count: 0,
    total_issue_count: 1,
    applied_gap_repair_count: 0,
    applied_duplicate_dedupe_count: 0,
    total_repair_count: 0,
    recommended_action: "review_required_wait_for_diagnostics",
  };
}

function pendingSummary(runId: string): Record<string, unknown> {
  return {
    preflight_run_id: runId,
    run_seq: 1,
    run_status: "preflight_running",
    acceptance_outcome: null,
    finished_at: null,
    blocking_issue_count: 0,
    review_required_issue_count: 0,
    warning_issue_count: 0,
    total_issue_count: 0,
    applied_gap_repair_count: 0,
    applied_duplicate_dedupe_count: 0,
    total_repair_count: 0,
    recommended_action: "preflight_in_progress",
  };
}

test.describe("DXF Prefilter E6-T2 - New Run Wizard project-ready filtering", () => {
  test("shows only project-ready linked files as stock/part options", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("p-e6-t2", "New Run Wizard Project-ready Filter"));
    mock.state.runsByProject["p-e6-t2"] = [];
    mock.state.filesByProject["p-e6-t2"] = [
      {
        id: "f-accepted-linked-1",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_linked_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-accepted-linked-1/source_linked_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:00:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-1"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: false,
          has_nesting_derivative: true,
          readiness_reason: "accepted_existing_part",
          suggested_code: "LINKED01",
          suggested_name: "Linked 01",
          source_label: "source_linked_01.dxf",
          existing_part_definition_id: "part-def-1",
          existing_part_revision_id: "part-rev-1",
          existing_part_code: "PART-001",
        },
      },
      {
        id: "f-accepted-linked-2",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_linked_02.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-accepted-linked-2/source_linked_02.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:01:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-2"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: false,
          has_nesting_derivative: true,
          readiness_reason: "accepted_existing_part",
          suggested_code: "LINKED02",
          suggested_name: "Linked 02",
          source_label: "source_linked_02.dxf",
          existing_part_definition_id: "part-def-2",
          existing_part_revision_id: "part-rev-2",
          existing_part_code: "PART-002",
        },
      },
      {
        id: "f-rejected-1",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_rejected_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-rejected-1/source_rejected_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:02:00Z",
        latest_preflight_summary: rejectedSummary("pf-rej-1"),
        latest_part_creation_projection: {
          acceptance_outcome: "preflight_rejected",
          part_creation_ready: false,
          has_nesting_derivative: false,
          readiness_reason: "not_eligible_rejected",
          suggested_code: "REJECTED01",
          suggested_name: "Rejected 01",
          source_label: "source_rejected_01.dxf",
        },
      },
      {
        id: "f-rejected-stale-linkage-1",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "Kor_D120-BodyPad.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-rejected-stale-linkage-1/Kor_D120-BodyPad.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:02:30Z",
        latest_preflight_summary: rejectedSummary("pf-rej-stale-1"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: false,
          has_nesting_derivative: true,
          readiness_reason: "accepted_existing_part",
          suggested_code: "KOR_D120_BODYPAD",
          suggested_name: "Kor D120 BodyPad",
          source_label: "Kor_D120-BodyPad.dxf",
          existing_part_definition_id: "part-def-stale-1",
          existing_part_revision_id: "part-rev-stale-1",
          existing_part_code: "PART-STALE-001",
        },
      },
      {
        id: "f-review-1",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_review_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-review-1/source_review_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:03:00Z",
        latest_preflight_summary: reviewSummary("pf-rev-1"),
        latest_part_creation_projection: {
          acceptance_outcome: "preflight_review_required",
          part_creation_ready: false,
          has_nesting_derivative: false,
          readiness_reason: "not_eligible_review_required",
          suggested_code: "REVIEW01",
          suggested_name: "Review 01",
          source_label: "source_review_01.dxf",
        },
      },
      {
        id: "f-pending-1",
        project_id: "p-e6-t2",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_pending_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t2/files/f-pending-1/source_pending_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-26T09:04:00Z",
        latest_preflight_summary: pendingSummary("pf-pend-1"),
        latest_part_creation_projection: {
          acceptance_outcome: null,
          part_creation_ready: false,
          has_nesting_derivative: false,
          readiness_reason: "not_eligible_preflight_pending",
          suggested_code: "PENDING01",
          suggested_name: "Pending 01",
          source_label: "source_pending_01.dxf",
        },
      },
    ];

    await page.goto("/projects/p-e6-t2");
    await page.getByRole("button", { name: "New run wizard" }).click();
    await expect(page.getByRole("heading", { name: "New run wizard" })).toBeVisible();

    const stockSelect = page.getByRole("combobox", { name: "Stock file" });
    await expect(stockSelect.locator("option", { hasText: "source_linked_01.dxf" })).toHaveCount(1);
    await expect(stockSelect.locator("option", { hasText: "source_linked_02.dxf" })).toHaveCount(1);
    await expect(stockSelect.locator("option", { hasText: "source_rejected_01.dxf" })).toHaveCount(0);
    await expect(stockSelect.locator("option", { hasText: "Kor_D120-BodyPad.dxf" })).toHaveCount(0);
    await expect(stockSelect.locator("option", { hasText: "source_review_01.dxf" })).toHaveCount(0);
    await expect(stockSelect.locator("option", { hasText: "source_pending_01.dxf" })).toHaveCount(0);

    await expect(page.locator("span", { hasText: "source_linked_01.dxf" })).toBeVisible();
    await expect(page.locator("span", { hasText: "source_linked_02.dxf" })).toBeVisible();
    await expect(page.locator('input[type="checkbox"]')).toHaveCount(2);
    await expect(page.locator("span", { hasText: "source_rejected_01.dxf" })).toHaveCount(0);
    await expect(page.locator("span", { hasText: "Kor_D120-BodyPad.dxf" })).toHaveCount(0);
    await expect(page.locator("span", { hasText: "source_review_01.dxf" })).toHaveCount(0);
    await expect(page.locator("span", { hasText: "source_pending_01.dxf" })).toHaveCount(0);

    const continueButton = page.getByRole("button", { name: "Continue to parameters" });
    await expect(continueButton).toBeDisabled();

    await page.locator('input[type="checkbox"]').first().check();
    await expect(continueButton).toBeEnabled();
    await continueButton.click();

    await page.getByRole("button", { name: "Continue to summary" }).click();
    await page.getByRole("button", { name: "Start run" }).click();

    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();
    await expect(page.getByText("Selected file has no linked part revision")).toHaveCount(0);
  });
});
