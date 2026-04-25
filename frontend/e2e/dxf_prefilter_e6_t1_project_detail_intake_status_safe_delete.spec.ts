import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

function acceptedSummary(runId: string): Record<string, unknown> {
  return {
    preflight_run_id: runId,
    run_seq: 1,
    run_status: "preflight_complete",
    acceptance_outcome: "accepted_for_import",
    finished_at: "2026-04-25T10:00:00Z",
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
    finished_at: "2026-04-25T10:05:00Z",
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
    finished_at: "2026-04-25T10:06:00Z",
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

test.describe("DXF Prefilter E6-T1 - Project Detail intake-aware status + safe hide", () => {
  test("shows intake truth and hides archived upload from active list", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("p-e6-t1", "Project Detail Intake Truth"));
    mock.state.runsByProject["p-e6-t1"] = [];
    mock.state.filesByProject["p-e6-t1"] = [
      {
        id: "f-accepted-linked-1",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_linked_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-linked-1/source_linked_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:00:00Z",
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
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_linked_02.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-linked-2/source_linked_02.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:01:00Z",
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
        id: "f-accepted-linked-3",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_linked_03.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-linked-3/source_linked_03.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:02:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-3"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: false,
          has_nesting_derivative: true,
          readiness_reason: "accepted_existing_part",
          suggested_code: "LINKED03",
          suggested_name: "Linked 03",
          source_label: "source_linked_03.dxf",
          existing_part_definition_id: "part-def-3",
          existing_part_revision_id: "part-rev-3",
          existing_part_code: "PART-003",
        },
      },
      {
        id: "f-accepted-ready-1",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_ready_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-ready-1/source_ready_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:03:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-4"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: true,
          has_nesting_derivative: true,
          readiness_reason: "accepted_ready",
          suggested_code: "READY01",
          suggested_name: "Ready 01",
          source_label: "source_ready_01.dxf",
        },
      },
      {
        id: "f-accepted-ready-2",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_ready_02.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-ready-2/source_ready_02.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:04:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-5"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: true,
          has_nesting_derivative: true,
          readiness_reason: "accepted_ready",
          suggested_code: "READY02",
          suggested_name: "Ready 02",
          source_label: "source_ready_02.dxf",
        },
      },
      {
        id: "f-accepted-pending-import",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_import_pending_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-accepted-pending-import/source_import_pending_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:05:00Z",
        latest_preflight_summary: acceptedSummary("pf-acc-6"),
        latest_part_creation_projection: {
          acceptance_outcome: "accepted_for_import",
          part_creation_ready: false,
          has_nesting_derivative: false,
          readiness_reason: "accepted_geometry_import_pending",
          suggested_code: "IMPORTPENDING01",
          suggested_name: "Import Pending 01",
          source_label: "source_import_pending_01.dxf",
        },
      },
      {
        id: "f-rejected-1",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_rejected_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-rejected-1/source_rejected_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:06:00Z",
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
        id: "f-review-1",
        project_id: "p-e6-t1",
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "source_review_01.dxf",
        storage_key: "users/e2e-user/projects/p-e6-t1/files/f-review-1/source_review_01.dxf",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: "2026-04-25T09:07:00Z",
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
    ];

    await page.goto("/projects/p-e6-t1");

    await expect(page.getByRole("heading", { name: "Project-ready files" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Intake attention" })).toBeVisible();

    // Not all rows are rendered as legacy pending.
    await expect(page.getByText("already created", { exact: true })).toHaveCount(3);
    await expect(page.getByText("ready for part creation", { exact: true })).toHaveCount(2);

    const projectReadySection = page
      .getByRole("heading", { name: "Project-ready files" })
      .locator("xpath=ancestor::section[1]");
    const intakeAttentionSection = page
      .getByRole("heading", { name: "Intake attention" })
      .locator("xpath=ancestor::section[1]");

    // Accepted/linked truth is visible.
    await expect(projectReadySection.getByText("source_linked_01.dxf")).toBeVisible();
    await expect(projectReadySection.getByText("source_ready_01.dxf")).toBeVisible();

    // Rejected/review sources are not shown as project-ready items.
    await expect(projectReadySection.getByText("source_rejected_01.dxf")).toHaveCount(0);
    await expect(projectReadySection.getByText("source_review_01.dxf")).toHaveCount(0);
    await expect(intakeAttentionSection.getByText("source_rejected_01.dxf")).toBeVisible();
    await expect(intakeAttentionSection.getByText("source_review_01.dxf")).toBeVisible();
    await expect(intakeAttentionSection.getByText("rejected", { exact: true })).toBeVisible();
    await expect(intakeAttentionSection.getByText("review required", { exact: true })).toBeVisible();

    // Hide upload should not trigger legacy delete error text and should remove row from active UI.
    const rejectedRow = intakeAttentionSection.locator("tr", { hasText: "source_rejected_01.dxf" });
    await rejectedRow.getByRole("button", { name: "Hide upload" }).click();

    await expect(intakeAttentionSection.getByText("source_rejected_01.dxf")).toHaveCount(0);
    await expect(page.getByText("delete file metadata failed")).toHaveCount(0);
  });
});
