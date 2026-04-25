import type { ProjectFile } from "./types";

// Canonical tone palette for the DxfIntake UX.
// success  = accepted / ready / 0 issues
// attention = review-required / ambiguous
// blocked  = rejected / error / blocking
// queued   = running / pending / queued
// neutral  = info / already-created / not eligible (no action needed)
export const TONE = {
  success: "bg-green-100 text-green-800",
  attention: "bg-amber-100 text-amber-800",
  blocked: "bg-red-100 text-red-800",
  queued: "bg-sky-100 text-sky-800",
  neutral: "bg-slate-100 text-slate-700",
} as const;

// Shared user-facing copy for the DxfIntake UX.
// Three distinct layers:
//   status      — what the file or run state is right now
//   next step   — what the user should do (actionable)
//   tech note   — backend/API truth that is not actionable guidance
export const INTAKE_COPY = {
  page: {
    subtitle: (name: string) => `${name}: upload source DXF files and track preflight status.`,
  },
  upload: {
    title: "Source DXF upload",
    helper: "Each uploaded file triggers preflight automatically after finalize — no manual trigger needed.",
    dropzone_primary: "Drag and drop source DXF files here",
    dropzone_secondary: "or click to open file picker",
  },
  settings: {
    title: "Preflight settings",
    helper: "These settings are attached to new uploads started on this page.",
    helper_tech: "Sent as rules_profile_snapshot_jsonb on upload finalize.",
    reset_label: "Reset to defaults",
  },
  runs: {
    empty: "No files uploaded yet. Upload a source DXF above to start preflight.",
    run_seq: (seq: number) => `Run #${seq}`,
    no_run_yet: "No run yet",
    col_next_step: "Next step",
    cta_open_review: "Open review",
    cta_view_diagnostics: "View diagnostics",
    review_na: "—",
  },
  acceptedParts: {
    title: "Accepted files → parts",
    helper: "Only accepted files appear here. Part creation uses the existing POST /projects/{project_id}/parts route.",
    empty: "No accepted files yet. Part creation becomes available once preflight accepts a file.",
    non_eligible_note: (review: number, rejected: number, pending: number) =>
      `Not eligible: ${review} review-required, ${rejected} rejected, ${pending} preflight pending.`,
    cta_create: "Create part",
    cta_creating: "Creating…",
    note_existing_part: (code: string) => `Already linked: ${code}.`,
    note_geometry_pending: "Geometry import still running — refresh after import finishes.",
  },
  diagnostics: {
    overlay_title: "Preflight diagnostics",
    overlay_subtitle: "Read-only snapshot of the latest preflight run for this file.",
    section_source: "Source inventory",
    section_roles: "Role mapping",
    section_issues: "Issues",
    section_repairs: "Repairs",
    section_acceptance: "Acceptance outcome",
    section_artifacts: "Artifacts",
    no_issues: "No normalized issues.",
    no_artifacts: "No artifact references.",
  },
  review: {
    overlay_title: "Review required",
    overlay_subtitle: "This file has ambiguous geometry that needs resolution before it can be accepted.",
    section_summary: "Review summary",
    section_issues: "Review-required issues",
    section_signals: "Remaining unresolved signals",
    guidance_title: "Recommended next step",
    guidance_body:
      "Submit a corrected source DXF using replacement upload below. Preflight re-runs automatically after finalize.",
    tech_note_title: "Technical note",
    tech_note_body:
      "Persisted review decision save is not implemented. This overlay is guidance and a replacement upload entry point only. Replacement finalize uses the existing complete_upload route with replaces_file_object_id.",
    section_replace: "Replace source DXF",
    replace_helper: "Upload a corrected DXF to re-run preflight from scratch.",
    cta_open_diagnostics: "Open full diagnostics",
    cta_upload_replacement: "Upload replacement DXF",
    none_label: "none",
  },
} as const;

// --- Badge helpers — presentation truth for all DxfIntake status surfaces ---

export function runStatusBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "not started", className: TONE.neutral };
  }
  const status = String(summary.run_status ?? "").trim().toLowerCase();
  if (status === "preflight_complete") {
    return { label: "complete", className: TONE.success };
  }
  if (status === "preflight_failed") {
    return { label: "failed", className: TONE.blocked };
  }
  if (status === "preflight_running" || status === "running" || status === "preflight_in_progress") {
    return { label: "running", className: TONE.queued };
  }
  if (status === "preflight_queued" || status === "queued") {
    return { label: "queued", className: TONE.queued };
  }
  if (status) {
    return { label: status.split("_").join(" "), className: TONE.queued };
  }
  return { label: "unknown", className: TONE.neutral };
}

export function acceptanceOutcomeBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "—", className: TONE.neutral };
  }
  if (summary.acceptance_outcome === "accepted_for_import") {
    return { label: "accepted", className: TONE.success };
  }
  if (summary.acceptance_outcome === "preflight_review_required") {
    return { label: "review required", className: TONE.attention };
  }
  if (summary.acceptance_outcome === "preflight_rejected") {
    return { label: "rejected", className: TONE.blocked };
  }
  if (summary.run_status && summary.run_status !== "preflight_complete") {
    return { label: "pending", className: TONE.queued };
  }
  return { label: "—", className: TONE.neutral };
}

export function issueCountBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "—", className: TONE.neutral };
  }
  const total = summary.total_issue_count;
  if (total <= 0) {
    return { label: "0 issues", className: TONE.success };
  }
  if (summary.blocking_issue_count > 0) {
    return { label: `${total} issues`, className: TONE.blocked };
  }
  if (summary.review_required_issue_count > 0) {
    return { label: `${total} issues`, className: TONE.attention };
  }
  return { label: `${total} issues`, className: TONE.queued };
}

// Repairs are informational — neutral tone, not an attention signal.
export function repairCountBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "—", className: TONE.neutral };
  }
  if (summary.total_repair_count <= 0) {
    return { label: "0 repairs", className: TONE.neutral };
  }
  return { label: `${summary.total_repair_count} repairs`, className: TONE.neutral };
}

export function recommendedNextStep(file: ProjectFile): string {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return "Waiting for preflight to start";
  }
  switch (summary.recommended_action) {
    case "ready_for_next_step":
      return "Ready — proceed to part creation";
    case "review_required_wait_for_diagnostics":
      return "Open review overlay to inspect issues";
    case "rejected_fix_and_reupload":
      return "Fix source DXF and re-upload";
    case "preflight_in_progress":
      return "Preflight running — check back shortly";
    case "preflight_not_started":
      return "Waiting for preflight to start";
    default:
      break;
  }
  if (summary.acceptance_outcome === "accepted_for_import") {
    return "Ready — proceed to part creation";
  }
  if (summary.acceptance_outcome === "preflight_review_required") {
    return "Open review overlay to inspect issues";
  }
  if (summary.acceptance_outcome === "preflight_rejected") {
    return "Fix source DXF and re-upload";
  }
  if (
    summary.run_status === "preflight_running" ||
    summary.run_status === "running" ||
    summary.run_status === "queued"
  ) {
    return "Preflight running — check back shortly";
  }
  return "Waiting for preflight to start";
}

export function partCreationReadinessBadge(
  file: ProjectFile,
): { label: string; className: string; description: string } {
  const projection = file.latest_part_creation_projection ?? null;
  if (!projection) {
    return {
      label: "not eligible",
      className: TONE.neutral,
      description: "Part-creation projection not available for this file.",
    };
  }
  switch (projection.readiness_reason) {
    case "accepted_ready":
      return {
        label: "ready",
        className: TONE.success,
        description: "Geometry validated — nesting derivative ready for part creation.",
      };
    case "accepted_geometry_import_pending":
      return {
        label: "pending",
        className: TONE.queued,
        description: "Geometry import still running. Refresh after import finishes.",
      };
    case "accepted_geometry_not_validated":
      return {
        label: "pending",
        className: TONE.attention,
        description: `Geometry status: ${projection.geometry_revision_status || "unknown"} — not validated yet.`,
      };
    case "accepted_missing_nesting_derivative":
      return {
        label: "pending",
        className: TONE.attention,
        description: "Nesting derivative not yet available for this accepted file.",
      };
    case "accepted_existing_part":
      return {
        label: "already created",
        className: TONE.neutral,
        description: `Part already linked (${projection.existing_part_code || projection.existing_part_definition_id || "existing definition"}).`,
      };
    case "not_eligible_review_required":
      return {
        label: "not eligible",
        className: TONE.attention,
        description: "Preflight is review-required — resolve via the review overlay first.",
      };
    case "not_eligible_rejected":
      return {
        label: "not eligible",
        className: TONE.blocked,
        description: "Preflight rejected this file — fix source DXF and re-upload.",
      };
    case "not_eligible_preflight_pending":
      return {
        label: "not eligible",
        className: TONE.queued,
        description: "Preflight is still running — part creation is not yet available.",
      };
    case "not_eligible_file_kind":
      return {
        label: "not eligible",
        className: TONE.neutral,
        description: "Only source DXF files are eligible for this flow.",
      };
    case "not_eligible_no_preflight_run":
      return {
        label: "not eligible",
        className: TONE.neutral,
        description: "No preflight run recorded for this file yet.",
      };
    default:
      return {
        label: "not eligible",
        className: TONE.neutral,
        description: "File is not eligible for part creation in the current state.",
      };
  }
}

export interface ProjectDetailIntakeStatus {
  statusLabel: string;
  statusClassName: string;
  nextStep: string;
  isProjectReady: boolean;
  isAttention: boolean;
  isLinkedPart: boolean;
}

export function projectDetailIntakeStatus(file: ProjectFile): ProjectDetailIntakeStatus {
  const projection = file.latest_part_creation_projection ?? null;
  const summary = file.latest_preflight_summary ?? null;
  const legacyValidationStatus = String(file.validation_status ?? "").trim().toLowerCase();

  if (!summary && legacyValidationStatus === "error") {
    return {
      statusLabel: "error",
      statusClassName: TONE.blocked,
      nextStep: file.validation_error || "Fix upload and try again.",
      isProjectReady: false,
      isAttention: true,
      isLinkedPart: false,
    };
  }

  const fileKind = String(file.file_type ?? "").trim().toLowerCase();
  if (fileKind !== "source_dxf") {
    return {
      statusLabel: legacyValidationStatus === "ok" ? "ok" : "uploaded",
      statusClassName: legacyValidationStatus === "ok" ? TONE.success : TONE.neutral,
      nextStep: "Available for project workflows.",
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: false,
    };
  }

  const outcome = String(summary?.acceptance_outcome ?? "").trim().toLowerCase();
  const runStatus = String(summary?.run_status ?? "").trim().toLowerCase();
  const readinessReason = String(projection?.readiness_reason ?? "").trim().toLowerCase();

  if (readinessReason === "accepted_existing_part") {
    return {
      statusLabel: "already created",
      statusClassName: TONE.neutral,
      nextStep: `Part linked (${projection?.existing_part_code || projection?.existing_part_definition_id || "existing part"}).`,
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: true,
    };
  }
  if (readinessReason === "accepted_ready") {
    return {
      statusLabel: "ready for part creation",
      statusClassName: TONE.success,
      nextStep: "Use DXF Intake to create part.",
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: false,
    };
  }
  if (readinessReason === "accepted_geometry_import_pending") {
    return {
      statusLabel: "geometry import pending",
      statusClassName: TONE.queued,
      nextStep: "Refresh after geometry import completes.",
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: false,
    };
  }
  if (readinessReason === "accepted_geometry_not_validated") {
    return {
      statusLabel: "accepted - geometry pending validation",
      statusClassName: TONE.attention,
      nextStep: "Check DXF Intake diagnostics for geometry state.",
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: false,
    };
  }
  if (readinessReason === "accepted_missing_nesting_derivative") {
    return {
      statusLabel: "accepted - derivative pending",
      statusClassName: TONE.attention,
      nextStep: "Refresh later or inspect DXF Intake diagnostics.",
      isProjectReady: true,
      isAttention: false,
      isLinkedPart: false,
    };
  }
  if (outcome === "preflight_rejected" || readinessReason === "not_eligible_rejected") {
    return {
      statusLabel: "rejected",
      statusClassName: TONE.blocked,
      nextStep: "Fix in DXF Intake and re-upload.",
      isProjectReady: false,
      isAttention: true,
      isLinkedPart: false,
    };
  }
  if (outcome === "preflight_review_required" || readinessReason === "not_eligible_review_required") {
    return {
      statusLabel: "review required",
      statusClassName: TONE.attention,
      nextStep: "Open DXF Intake review flow.",
      isProjectReady: false,
      isAttention: true,
      isLinkedPart: false,
    };
  }
  if (!summary || readinessReason === "not_eligible_no_preflight_run") {
    return {
      statusLabel: "preflight pending",
      statusClassName: TONE.queued,
      nextStep: "Wait for preflight or open DXF Intake.",
      isProjectReady: false,
      isAttention: true,
      isLinkedPart: false,
    };
  }
  if (
    runStatus === "preflight_queued" ||
    runStatus === "queued" ||
    runStatus === "preflight_running" ||
    runStatus === "running" ||
    runStatus === "preflight_in_progress" ||
    readinessReason === "not_eligible_preflight_pending"
  ) {
    return {
      statusLabel: "preflight pending",
      statusClassName: TONE.queued,
      nextStep: "Preflight is running - check back shortly.",
      isProjectReady: false,
      isAttention: true,
      isLinkedPart: false,
    };
  }

  return {
    statusLabel: "intake attention",
    statusClassName: TONE.attention,
    nextStep: recommendedNextStep(file),
    isProjectReady: false,
    isAttention: true,
    isLinkedPart: false,
  };
}
