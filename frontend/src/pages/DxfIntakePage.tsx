import { useEffect, useMemo, useState } from "react";
import type { DragEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type {
  PreflightRulesProfileSnapshot,
  PreflightSettingsDraft,
  Project,
  ProjectFile,
} from "../lib/types";

interface UploadProgressState {
  total: number;
  done: number;
  status: string;
}

const DEFAULT_PREFLIGHT_SETTINGS_DRAFT: PreflightSettingsDraft = {
  strict_mode: false,
  auto_repair_enabled: false,
  interactive_review_on_ambiguity: true,
  max_gap_close_mm: 1.0,
  duplicate_contour_merge_tolerance_mm: 0.05,
  cut_color_map_text: "",
  marking_color_map_text: "",
};

function createDefaultPreflightSettingsDraft(): PreflightSettingsDraft {
  return { ...DEFAULT_PREFLIGHT_SETTINGS_DRAFT };
}

function parseAciColorMap(raw: string, fieldName: "cut_color_map" | "marking_color_map"): number[] {
  const tokens = raw
    .split(",")
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
  const values: number[] = [];
  const seen = new Set<number>();
  for (const token of tokens) {
    if (!/^\d+$/.test(token)) {
      throw new Error(`${fieldName} must be a comma-separated list of integer ACI values.`);
    }
    const value = Number(token);
    if (!Number.isInteger(value) || value < 0 || value > 256) {
      throw new Error(`${fieldName} entries must be integers in range [0, 256].`);
    }
    if (!seen.has(value)) {
      values.push(value);
      seen.add(value);
    }
  }
  return values;
}

function buildRulesProfileSnapshotFromDraft(draft: PreflightSettingsDraft): PreflightRulesProfileSnapshot {
  const maxGap = Number(draft.max_gap_close_mm);
  if (!Number.isFinite(maxGap) || maxGap <= 0) {
    throw new Error("max_gap_close_mm must be a positive number.");
  }

  const duplicateTolerance = Number(draft.duplicate_contour_merge_tolerance_mm);
  if (!Number.isFinite(duplicateTolerance) || duplicateTolerance <= 0) {
    throw new Error("duplicate_contour_merge_tolerance_mm must be a positive number.");
  }

  return {
    strict_mode: draft.strict_mode,
    auto_repair_enabled: draft.auto_repair_enabled,
    interactive_review_on_ambiguity: draft.interactive_review_on_ambiguity,
    max_gap_close_mm: maxGap,
    duplicate_contour_merge_tolerance_mm: duplicateTolerance,
    cut_color_map: parseAciColorMap(draft.cut_color_map_text, "cut_color_map"),
    marking_color_map: parseAciColorMap(draft.marking_color_map_text, "marking_color_map"),
  };
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

async function uploadFileToSignedUrl(uploadUrl: string, file: File, token: string): Promise<void> {
  const headers = {
    "Content-Type": file.type || "application/octet-stream",
    Authorization: `Bearer ${token}`,
  };

  const putResponse = await fetch(uploadUrl, {
    method: "PUT",
    headers,
    body: file,
  });
  if (putResponse.ok) {
    return;
  }

  const postResponse = await fetch(uploadUrl, {
    method: "POST",
    headers,
    body: file,
  });
  if (!postResponse.ok) {
    const body = await postResponse.text();
    throw new Error(body || `Upload failed (${postResponse.status}).`);
  }
}

function formatRunStatusBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return {
      label: "not started",
      className: "bg-slate-100 text-slate-700",
    };
  }

  const runStatus = String(summary.run_status ?? "").trim().toLowerCase();
  if (runStatus === "preflight_complete") {
    return {
      label: "preflight complete",
      className: "bg-green-100 text-green-800",
    };
  }
  if (runStatus === "preflight_failed") {
    return {
      label: "preflight failed",
      className: "bg-red-100 text-red-800",
    };
  }
  if (runStatus === "preflight_running" || runStatus === "running" || runStatus === "preflight_in_progress") {
    return {
      label: "running",
      className: "bg-sky-100 text-sky-800",
    };
  }
  if (runStatus === "preflight_queued" || runStatus === "queued") {
    return {
      label: "queued",
      className: "bg-amber-100 text-amber-800",
    };
  }
  if (runStatus) {
    return {
      label: runStatus.split("_").join(" "),
      className: "bg-sky-100 text-sky-800",
    };
  }
  return { label: "unknown", className: "bg-slate-100 text-slate-700" };
}

function formatAcceptanceOutcomeBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "not available", className: "bg-slate-100 text-slate-700" };
  }
  if (summary.acceptance_outcome === "accepted_for_import") {
    return { label: "accepted", className: "bg-green-100 text-green-800" };
  }
  if (summary.acceptance_outcome === "preflight_review_required") {
    return { label: "review required", className: "bg-amber-100 text-amber-800" };
  }
  if (summary.acceptance_outcome === "preflight_rejected") {
    return { label: "rejected", className: "bg-red-100 text-red-800" };
  }
  if (summary.run_status && summary.run_status !== "preflight_complete") {
    return { label: "pending", className: "bg-sky-100 text-sky-800" };
  }
  return { label: "not available", className: "bg-slate-100 text-slate-700" };
}

function formatIssueCountBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "no data", className: "bg-slate-100 text-slate-700" };
  }
  const total = summary.total_issue_count;
  if (total <= 0) {
    return { label: "0 issues", className: "bg-green-100 text-green-800" };
  }
  if (summary.blocking_issue_count > 0) {
    return { label: `${total} issues`, className: "bg-red-100 text-red-800" };
  }
  if (summary.review_required_issue_count > 0) {
    return { label: `${total} issues`, className: "bg-amber-100 text-amber-800" };
  }
  return { label: `${total} issues`, className: "bg-sky-100 text-sky-800" };
}

function formatRepairCountBadge(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return { label: "no data", className: "bg-slate-100 text-slate-700" };
  }
  if (summary.total_repair_count <= 0) {
    return { label: "0 repairs", className: "bg-slate-100 text-slate-700" };
  }
  return { label: `${summary.total_repair_count} repairs`, className: "bg-indigo-100 text-indigo-800" };
}

function formatRecommendedActionLabel(file: ProjectFile): string {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return "Upload complete; waiting for preflight";
  }
  switch (summary.recommended_action) {
    case "ready_for_next_step":
      return "Ready for next step";
    case "review_required_wait_for_diagnostics":
      return "Wait for diagnostics";
    case "rejected_fix_and_reupload":
      return "Fix source DXF and re-upload";
    case "preflight_in_progress":
      return "Preflight still running";
    case "preflight_not_started":
      return "Upload complete; waiting for preflight";
    default:
      break;
  }
  if (summary.acceptance_outcome === "accepted_for_import") {
    return "Ready for next step";
  }
  if (summary.acceptance_outcome === "preflight_review_required") {
    return "Wait for diagnostics";
  }
  if (summary.acceptance_outcome === "preflight_rejected") {
    return "Fix source DXF and re-upload";
  }
  if (summary.run_status === "preflight_running" || summary.run_status === "running" || summary.run_status === "queued") {
    return "Preflight still running";
  }
  return "Upload complete; waiting for preflight";
}

function formatExistsLabel(exists: boolean): string {
  return exists ? "yes" : "no";
}

function canOpenConditionalReviewModal(file: ProjectFile): boolean {
  return file.latest_preflight_summary?.acceptance_outcome === "preflight_review_required" && !!file.latest_preflight_diagnostics;
}

function formatSignalRecord(signal: Record<string, unknown>): string {
  const entries = Object.entries(signal);
  if (entries.length === 0) {
    return "empty signal";
  }
  return entries
    .map(([key, value]) => `${key}=${String(value ?? "-")}`)
    .join(" | ");
}

export function DxfIntakePage() {
  const { projectId } = useParams<{ projectId: string }>();

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<PreflightSettingsDraft>(() => createDefaultPreflightSettingsDraft());
  const [selectedDiagnosticsFileId, setSelectedDiagnosticsFileId] = useState<string | null>(null);
  const [selectedReviewFileId, setSelectedReviewFileId] = useState<string | null>(null);
  const [reviewReplacementFile, setReviewReplacementFile] = useState<File | null>(null);
  const [reviewReplacementStatus, setReviewReplacementStatus] = useState("");
  const [reviewReplacementError, setReviewReplacementError] = useState("");
  const [reviewReplacementUploading, setReviewReplacementUploading] = useState(false);

  async function loadData() {
    if (!projectId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const [projectResponse, filesResponse] = await Promise.all([
        api.getProject(token, projectId),
        api.listProjectFiles(token, projectId, {
          include_preflight_summary: true,
          include_preflight_diagnostics: true,
        }),
      ]);
      setProject(projectResponse);
      setFiles(filesResponse.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load DXF intake data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [projectId]);

  useEffect(() => {
    if (!selectedDiagnosticsFileId) {
      return;
    }
    const selected = files.find((file) => file.id === selectedDiagnosticsFileId);
    if (!selected || !selected.latest_preflight_diagnostics) {
      setSelectedDiagnosticsFileId(null);
    }
  }, [files, selectedDiagnosticsFileId]);

  useEffect(() => {
    if (!selectedReviewFileId) {
      return;
    }
    const selected = files.find((file) => file.id === selectedReviewFileId);
    if (!selected || !canOpenConditionalReviewModal(selected)) {
      setSelectedReviewFileId(null);
      setReviewReplacementFile(null);
      setReviewReplacementStatus("");
      setReviewReplacementError("");
      setReviewReplacementUploading(false);
    }
  }, [files, selectedReviewFileId]);

  async function handleFilesSelected(fileList: FileList | null) {
    if (!projectId || !fileList || fileList.length === 0) {
      return;
    }

    const selected = Array.from(fileList);
    let rulesProfileSnapshot: PreflightRulesProfileSnapshot;
    try {
      rulesProfileSnapshot = buildRulesProfileSnapshotFromDraft(settingsDraft);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid preflight settings.");
      return;
    }

    setUploadProgress({ total: selected.length, done: 0, status: "Preparing source DXF upload..." });
    setError("");

    try {
      const token = await getAccessToken();
      for (let index = 0; index < selected.length; index += 1) {
        const file = selected[index];
        setUploadProgress({
          total: selected.length,
          done: index,
          status: `Requesting signed URL for ${file.name}`,
        });

        const signed = await api.createUploadUrl(token, projectId, {
          filename: file.name,
          content_type: file.type || "application/dxf",
          size_bytes: file.size,
          file_type: "source_dxf",
        });

        setUploadProgress({
          total: selected.length,
          done: index,
          status: `Uploading ${file.name}`,
        });
        await uploadFileToSignedUrl(signed.upload_url, file, token);

        setUploadProgress({
          total: selected.length,
          done: index,
          status: `Finalizing ${file.name}`,
        });
        await api.completeUpload(token, projectId, {
          file_id: signed.file_id,
          original_filename: file.name,
          storage_key: signed.storage_key,
          file_type: "source_dxf",
          size_bytes: file.size,
          content_hash_sha256: null,
          rules_profile_snapshot_jsonb: rulesProfileSnapshot,
        });

        setUploadProgress({
          total: selected.length,
          done: index + 1,
          status: `Uploaded ${file.name}`,
        });
      }

      await loadData();
      setUploadProgress({
        total: selected.length,
        done: selected.length,
        status: "Upload complete. Preflight starts automatically.",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Source DXF upload failed.");
    }
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
    void handleFilesSelected(event.dataTransfer.files);
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
  }

  function handleResetSettings(): void {
    setSettingsDraft(createDefaultPreflightSettingsDraft());
  }

  function openConditionalReviewModal(fileId: string): void {
    setSelectedReviewFileId(fileId);
    setReviewReplacementFile(null);
    setReviewReplacementStatus("");
    setReviewReplacementError("");
    setReviewReplacementUploading(false);
  }

  function closeConditionalReviewModal(): void {
    setSelectedReviewFileId(null);
    setReviewReplacementFile(null);
    setReviewReplacementStatus("");
    setReviewReplacementError("");
    setReviewReplacementUploading(false);
  }

  function handleReviewReplacementFileChange(fileList: FileList | null): void {
    const selectedFile = fileList && fileList.length > 0 ? fileList[0] : null;
    setReviewReplacementFile(selectedFile);
    setReviewReplacementStatus("");
    setReviewReplacementError("");
  }

  async function handleReviewReplacementUpload(): Promise<void> {
    if (!projectId || reviewReplacementUploading) {
      return;
    }
    const selectedReviewFile = files.find((file) => file.id === selectedReviewFileId);
    if (!selectedReviewFile || !canOpenConditionalReviewModal(selectedReviewFile)) {
      setReviewReplacementError("Selected review file is no longer eligible for replacement review.");
      return;
    }
    if (!reviewReplacementFile) {
      setReviewReplacementError("Select a replacement DXF file before upload.");
      return;
    }

    let rulesProfileSnapshot: PreflightRulesProfileSnapshot;
    try {
      rulesProfileSnapshot = buildRulesProfileSnapshotFromDraft(settingsDraft);
    } catch (err) {
      setReviewReplacementError(err instanceof Error ? err.message : "Invalid preflight settings.");
      return;
    }

    setReviewReplacementUploading(true);
    setReviewReplacementError("");
    setReviewReplacementStatus("Requesting replacement upload slot...");

    try {
      const token = await getAccessToken();
      const signed = await api.replaceProjectFile(token, projectId, selectedReviewFile.id, {
        filename: reviewReplacementFile.name,
        content_type: reviewReplacementFile.type || "application/dxf",
        size_bytes: reviewReplacementFile.size,
      });

      setReviewReplacementStatus(`Uploading ${reviewReplacementFile.name}...`);
      await uploadFileToSignedUrl(signed.upload_url, reviewReplacementFile, token);

      setReviewReplacementStatus(`Finalizing ${reviewReplacementFile.name}...`);
      await api.completeUpload(token, projectId, {
        file_id: signed.file_id,
        original_filename: reviewReplacementFile.name,
        storage_key: signed.storage_path,
        file_type: "source_dxf",
        size_bytes: reviewReplacementFile.size,
        content_hash_sha256: null,
        replaces_file_object_id: signed.replaces_file_id,
        rules_profile_snapshot_jsonb: rulesProfileSnapshot,
      });

      setReviewReplacementStatus("Replacement uploaded. Refreshing latest preflight state...");
      await loadData();
      setReviewReplacementStatus("Replacement complete. Preflight rerun starts automatically.");
      setReviewReplacementFile(null);
    } catch (err) {
      setReviewReplacementError(err instanceof Error ? err.message : "Replacement upload failed.");
    } finally {
      setReviewReplacementUploading(false);
    }
  }

  const uploadPercent = useMemo(() => {
    if (!uploadProgress || uploadProgress.total <= 0) {
      return 0;
    }
    return Math.round((uploadProgress.done / uploadProgress.total) * 100);
  }, [uploadProgress]);

  const selectedDiagnosticsFile = useMemo(
    () => files.find((file) => file.id === selectedDiagnosticsFileId) ?? null,
    [files, selectedDiagnosticsFileId]
  );
  const selectedDiagnostics = selectedDiagnosticsFile?.latest_preflight_diagnostics ?? null;
  const selectedReviewFile = useMemo(
    () => files.find((file) => file.id === selectedReviewFileId) ?? null,
    [files, selectedReviewFileId]
  );
  const selectedReviewDiagnostics = selectedReviewFile?.latest_preflight_diagnostics ?? null;
  const selectedReviewSummary = selectedReviewFile?.latest_preflight_summary ?? null;
  const reviewRequiredIssues = useMemo(() => {
    if (!selectedReviewDiagnostics) {
      return [];
    }
    return selectedReviewDiagnostics.issue_summary.normalized_issues.filter(
      (issue) => String(issue.severity ?? "").trim().toLowerCase() === "review_required"
    );
  }, [selectedReviewDiagnostics]);
  const remainingReviewSignals = selectedReviewDiagnostics?.repair_summary.remaining_review_required_signals ?? [];

  if (!projectId) {
    return (
      <p className="rounded-md border border-danger/40 bg-red-50 px-4 py-3 text-danger">
        Missing project id in route.
      </p>
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">DXF Intake / Project Preparation</h1>
          <p className="mt-1 text-sm text-slate">
            {project?.name ?? "Project"}: source DXF upload and latest preflight status in one place.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}`}>
            Back to project
          </Link>
          <button className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" onClick={() => void loadData()} type="button">
            Refresh
          </button>
        </div>
      </header>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading && <p className="rounded-md border border-mist bg-white px-3 py-2 text-sm text-slate">Loading intake data...</p>}

      {!loading && (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header>
              <h2 className="text-lg font-semibold">Source DXF upload</h2>
              <p className="mt-1 text-sm text-slate">
                Uploading a source DXF automatically starts preflight after finalize. No manual preflight trigger is required.
              </p>
            </header>

            <label
              className={`flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-6 text-center ${
                dragActive ? "border-accent bg-sky-50" : "border-mist bg-slate-50"
              }`}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <input
                className="hidden"
                multiple
                onChange={(event) => void handleFilesSelected(event.target.files)}
                type="file"
              />
              <p className="text-sm font-medium text-ink">Drag and drop source DXF files here</p>
              <p className="mt-1 text-xs text-slate">or click to open file picker</p>
            </label>

            {uploadProgress && (
              <div className="rounded-md border border-mist bg-slate-50 px-3 py-2">
                <p className="text-sm text-slate">{uploadProgress.status}</p>
                <p className="mt-1 text-xs text-slate">
                  Progress: {uploadProgress.done}/{uploadProgress.total} ({uploadPercent}%)
                </p>
              </div>
            )}

            <div className="rounded-md border border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
              <p className="font-medium text-ink">Preflight settings (upload-session draft)</p>
              <p className="mt-1">
                These values are sent as <code>rules_profile_snapshot_jsonb</code> during upload finalize from this page.
                They apply to new source DXF uploads started here.
              </p>

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <label className="flex items-center gap-2 rounded border border-mist bg-white px-3 py-2">
                  <input
                    checked={settingsDraft.strict_mode}
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        strict_mode: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="font-mono text-xs text-slate">strict_mode</span>
                  </span>
                </label>
                <label className="flex items-center gap-2 rounded border border-mist bg-white px-3 py-2">
                  <input
                    checked={settingsDraft.auto_repair_enabled}
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        auto_repair_enabled: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="font-mono text-xs text-slate">auto_repair_enabled</span>
                  </span>
                </label>
                <label className="flex items-center gap-2 rounded border border-mist bg-white px-3 py-2 sm:col-span-2">
                  <input
                    checked={settingsDraft.interactive_review_on_ambiguity}
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        interactive_review_on_ambiguity: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  <span>
                    <span className="font-mono text-xs text-slate">interactive_review_on_ambiguity</span>
                  </span>
                </label>
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="space-y-1">
                  <span className="font-mono text-xs text-slate">max_gap_close_mm</span>
                  <input
                    className="w-full rounded border border-mist bg-white px-2 py-1"
                    min={0.000001}
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        max_gap_close_mm: Number(event.target.value),
                      }))
                    }
                    step="0.01"
                    type="number"
                    value={settingsDraft.max_gap_close_mm}
                  />
                </label>
                <label className="space-y-1">
                  <span className="font-mono text-xs text-slate">duplicate_contour_merge_tolerance_mm</span>
                  <input
                    className="w-full rounded border border-mist bg-white px-2 py-1"
                    min={0.000001}
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        duplicate_contour_merge_tolerance_mm: Number(event.target.value),
                      }))
                    }
                    step="0.001"
                    type="number"
                    value={settingsDraft.duplicate_contour_merge_tolerance_mm}
                  />
                </label>
              </div>

              <div className="mt-3 grid gap-3">
                <label className="space-y-1">
                  <span className="font-mono text-xs text-slate">cut_color_map</span>
                  <input
                    className="w-full rounded border border-mist bg-white px-2 py-1"
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        cut_color_map_text: event.target.value,
                      }))
                    }
                    placeholder="e.g. 1,3,7"
                    type="text"
                    value={settingsDraft.cut_color_map_text}
                  />
                </label>
                <label className="space-y-1">
                  <span className="font-mono text-xs text-slate">marking_color_map</span>
                  <input
                    className="w-full rounded border border-mist bg-white px-2 py-1"
                    onChange={(event) =>
                      setSettingsDraft((prev) => ({
                        ...prev,
                        marking_color_map_text: event.target.value,
                      }))
                    }
                    placeholder="e.g. 2,4,6"
                    type="text"
                    value={settingsDraft.marking_color_map_text}
                  />
                </label>
                <p className="text-xs text-slate">
                  Comma-separated ACI indices in range <code>[0,256]</code>.
                </p>
              </div>

              <div className="mt-3">
                <button
                  className="rounded border border-mist bg-white px-3 py-1.5 text-xs font-medium text-slate hover:bg-slate-100"
                  onClick={handleResetSettings}
                  type="button"
                >
                  Reset to defaults
                </button>
              </div>
            </div>
          </article>

          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Latest preflight runs</h2>
              <span className="text-sm text-slate">{files.length} files</span>
            </header>

            {files.length === 0 && (
              <p className="rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
                No files uploaded yet.
              </p>
            )}

            {files.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1080px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-mist text-left text-slate">
                      <th className="py-2">Filename</th>
                      <th className="py-2">Run status</th>
                      <th className="py-2">Issues</th>
                      <th className="py-2">Repairs</th>
                      <th className="py-2">Acceptance</th>
                      <th className="py-2">Recommended action</th>
                      <th className="py-2">Finished</th>
                      <th className="py-2">Review</th>
                      <th className="py-2">Diagnostics</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((file) => {
                      const summary = file.latest_preflight_summary;
                      const diagnostics = file.latest_preflight_diagnostics;
                      const canViewDiagnostics = !!diagnostics;
                      const runStatusBadge = formatRunStatusBadge(file);
                      const issueBadge = formatIssueCountBadge(file);
                      const repairBadge = formatRepairCountBadge(file);
                      const acceptanceBadge = formatAcceptanceOutcomeBadge(file);
                      const recommendedAction = formatRecommendedActionLabel(file);
                      const canOpenReview = canOpenConditionalReviewModal(file);
                      return (
                        <tr className="border-b border-mist/70" key={file.id}>
                          <td className="py-3">{file.original_filename}</td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${runStatusBadge.className}`}>
                              {runStatusBadge.label}
                            </span>
                            <p className="mt-1 text-xs text-slate">{summary?.run_seq ? `Run #${summary.run_seq}` : "No run yet"}</p>
                          </td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${issueBadge.className}`}>{issueBadge.label}</span>
                            <p className="mt-1 text-xs text-slate">
                              B:{summary?.blocking_issue_count ?? 0} R:{summary?.review_required_issue_count ?? 0} W:{summary?.warning_issue_count ?? 0}
                            </p>
                          </td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${repairBadge.className}`}>{repairBadge.label}</span>
                            <p className="mt-1 text-xs text-slate">
                              gap:{summary?.applied_gap_repair_count ?? 0} dedupe:{summary?.applied_duplicate_dedupe_count ?? 0}
                            </p>
                          </td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${acceptanceBadge.className}`}>
                              {acceptanceBadge.label}
                            </span>
                          </td>
                          <td className="py-3 text-sm text-slate">
                            {recommendedAction}
                          </td>
                          <td className="py-3">{formatDate(file.latest_preflight_summary?.finished_at ?? null)}</td>
                          <td className="py-3">
                            {canOpenReview ? (
                              <button
                                className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
                                onClick={() => openConditionalReviewModal(file.id)}
                                type="button"
                              >
                                Open review
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">n/a</span>
                            )}
                          </td>
                          <td className="py-3">
                            <button
                              className={`rounded border px-2 py-1 text-xs font-medium ${
                                canViewDiagnostics
                                  ? "border-mist bg-white text-slate hover:bg-slate-100"
                                  : "cursor-not-allowed border-mist/70 bg-slate-100 text-slate-400"
                              }`}
                              disabled={!canViewDiagnostics}
                              onClick={() => setSelectedDiagnosticsFileId(file.id)}
                              type="button"
                            >
                              View diagnostics
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </div>
      )}

      {selectedReviewFile && selectedReviewDiagnostics && selectedReviewSummary && canOpenConditionalReviewModal(selectedReviewFile) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl border border-mist bg-white p-5 shadow-xl">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4 border-b border-mist pb-4">
              <div>
                <h2 className="text-xl font-semibold">Conditional review modal</h2>
                <p className="mt-1 text-sm text-slate">{selectedReviewFile.original_filename}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-medium ${formatAcceptanceOutcomeBadge(selectedReviewFile).className}`}>
                    {formatAcceptanceOutcomeBadge(selectedReviewFile).label}
                  </span>
                  <span className={`rounded px-2 py-1 text-xs font-medium ${formatRunStatusBadge(selectedReviewFile).className}`}>
                    {formatRunStatusBadge(selectedReviewFile).label}
                  </span>
                  <span className="text-xs text-slate">{selectedReviewSummary.run_seq ? `Run #${selectedReviewSummary.run_seq}` : "Run n/a"}</span>
                  <span className="text-xs text-slate">Finished: {formatDate(selectedReviewSummary.finished_at ?? null)}</span>
                </div>
              </div>
              <button
                className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100"
                onClick={closeConditionalReviewModal}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="space-y-4">
              <section className="rounded-lg border border-mist bg-slate-50 p-4">
                <h3 className="text-sm font-semibold text-ink">Review summary</h3>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Review-required issues: {selectedReviewSummary.review_required_issue_count}</p>
                  <p>Remaining review-required signals: {selectedReviewDiagnostics.repair_summary.counts.remaining_review_required_signal_count}</p>
                  <p>Recommended action: {formatRecommendedActionLabel(selectedReviewFile)}</p>
                  <p>Precedence rule: {selectedReviewDiagnostics.acceptance_summary.precedence_rule_applied || "-"}</p>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Review-required issues</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {reviewRequiredIssues.length === 0 && <li>none</li>}
                  {reviewRequiredIssues.map((issue, index) => (
                    <li key={`${issue.code}-${index}`}>
                      [{issue.family || "-"} / {issue.code || "-"}] {issue.message || "-"}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Remaining review-required signals</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {remainingReviewSignals.length === 0 && <li>none</li>}
                  {remainingReviewSignals.map((signal, index) => (
                    <li key={`remaining-review-signal-${index}`}>{formatSignalRecord(signal)}</li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
                <h3 className="text-sm font-semibold text-amber-900">What to do now</h3>
                <p className="mt-2">
                  Current-code note: persisted review decision save is not implemented yet. This modal provides guidance and a replacement
                  upload entrypoint only.
                </p>
                <p className="mt-1">
                  Use replacement upload to submit a corrected source DXF. Finalize still goes through the existing
                  <code> complete_upload </code>
                  route with <code>replaces_file_object_id</code> and the current <code>rules_profile_snapshot_jsonb</code>.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="rounded border border-mist bg-white px-3 py-1.5 text-xs font-medium text-slate hover:bg-slate-100"
                    onClick={() => {
                      setSelectedDiagnosticsFileId(selectedReviewFile.id);
                      closeConditionalReviewModal();
                    }}
                    type="button"
                  >
                    Open full diagnostics drawer
                  </button>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Replace source DXF</h3>
                <p className="mt-2 text-xs text-slate">
                  This uses <code>POST /projects/{`{project_id}`}/files/{`{file_id}`}/replace</code> then signed upload and finalize.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <input
                    accept=".dxf"
                    className="max-w-full rounded border border-mist px-2 py-1 text-xs"
                    disabled={reviewReplacementUploading}
                    onChange={(event) => handleReviewReplacementFileChange(event.target.files)}
                    type="file"
                  />
                  <button
                    className={`rounded px-3 py-1.5 text-xs font-medium ${
                      reviewReplacementUploading
                        ? "cursor-not-allowed border border-mist/70 bg-slate-100 text-slate-400"
                        : "border border-accent bg-sky-50 text-accent hover:bg-sky-100"
                    }`}
                    disabled={reviewReplacementUploading || !reviewReplacementFile}
                    onClick={() => void handleReviewReplacementUpload()}
                    type="button"
                  >
                    Upload replacement DXF
                  </button>
                </div>
                {reviewReplacementFile && <p className="mt-2 text-xs text-slate">Selected file: {reviewReplacementFile.name}</p>}
                {reviewReplacementStatus && <p className="mt-2 text-xs text-slate">{reviewReplacementStatus}</p>}
                {reviewReplacementError && (
                  <p className="mt-2 rounded border border-danger/40 bg-red-50 px-2 py-1 text-xs text-danger">{reviewReplacementError}</p>
                )}
              </section>
            </div>
          </div>
        </div>
      )}

      {selectedDiagnosticsFile && selectedDiagnostics && (
        <div className="fixed inset-0 z-40 flex justify-end bg-ink/40">
          <div className="h-full w-full max-w-3xl overflow-y-auto border-l border-mist bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-4 border-b border-mist pb-4">
              <div>
                <h2 className="text-xl font-semibold">Diagnostics</h2>
                <p className="mt-1 text-sm text-slate">{selectedDiagnosticsFile.original_filename}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-medium ${formatRunStatusBadge(selectedDiagnosticsFile).className}`}>
                    {formatRunStatusBadge(selectedDiagnosticsFile).label}
                  </span>
                  <span className={`rounded px-2 py-1 text-xs font-medium ${formatAcceptanceOutcomeBadge(selectedDiagnosticsFile).className}`}>
                    {formatAcceptanceOutcomeBadge(selectedDiagnosticsFile).label}
                  </span>
                  <span className="text-xs text-slate">
                    {selectedDiagnosticsFile.latest_preflight_summary?.run_seq
                      ? `Run #${selectedDiagnosticsFile.latest_preflight_summary.run_seq}`
                      : "Run n/a"}
                  </span>
                  <span className="text-xs text-slate">
                    Finished: {formatDate(selectedDiagnosticsFile.latest_preflight_summary?.finished_at ?? null)}
                  </span>
                </div>
              </div>
              <button
                className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100"
                onClick={() => setSelectedDiagnosticsFileId(null)}
                type="button"
              >
                Close
              </button>
            </div>

            <div className="space-y-5">
              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Source inventory</h3>
                <p className="mt-2 text-xs text-slate">
                  Layers: {selectedDiagnostics.source_inventory_summary.found_layers.join(", ") || "-"}
                </p>
                <p className="mt-1 text-xs text-slate">
                  Colors: {selectedDiagnostics.source_inventory_summary.found_colors.join(", ") || "-"}
                </p>
                <p className="mt-1 text-xs text-slate">
                  Linetypes: {selectedDiagnostics.source_inventory_summary.found_linetypes.join(", ") || "-"}
                </p>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Entity count: {selectedDiagnostics.source_inventory_summary.entity_count}</p>
                  <p>Contour count: {selectedDiagnostics.source_inventory_summary.contour_count}</p>
                  <p>Open-path layers: {selectedDiagnostics.source_inventory_summary.open_path_layer_count}</p>
                  <p>Open-path total: {selectedDiagnostics.source_inventory_summary.open_path_total_count}</p>
                  <p>Duplicate groups: {selectedDiagnostics.source_inventory_summary.duplicate_candidate_group_count}</p>
                  <p>Duplicate members: {selectedDiagnostics.source_inventory_summary.duplicate_candidate_member_count}</p>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Role mapping</h3>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Review-required count: {selectedDiagnostics.role_mapping_summary.review_required_count}</p>
                  <p>Blocking conflict count: {selectedDiagnostics.role_mapping_summary.blocking_conflict_count}</p>
                </div>
                <p className="mt-2 text-xs font-medium text-ink">Resolved role inventory</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-slate">
                  {Object.keys(selectedDiagnostics.role_mapping_summary.resolved_role_inventory).length === 0 && <li>none</li>}
                  {Object.entries(selectedDiagnostics.role_mapping_summary.resolved_role_inventory).map(([role, count]) => (
                    <li key={role}>
                      {role}: {count}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs font-medium text-ink">Layer role assignments</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-slate">
                  {selectedDiagnostics.role_mapping_summary.layer_role_assignments.length === 0 && <li>none</li>}
                  {selectedDiagnostics.role_mapping_summary.layer_role_assignments.map((assignment, index) => (
                    <li key={`${index}-${String(assignment.layer ?? "layer")}`}>
                      layer={String(assignment.layer ?? "-")} role={String(assignment.role ?? "-")}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Issues</h3>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Blocking: {selectedDiagnostics.issue_summary.counts_by_severity.blocking}</p>
                  <p>Review required: {selectedDiagnostics.issue_summary.counts_by_severity.review_required}</p>
                  <p>Warning: {selectedDiagnostics.issue_summary.counts_by_severity.warning}</p>
                  <p>Info: {selectedDiagnostics.issue_summary.counts_by_severity.info}</p>
                </div>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[520px] border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-mist text-left text-slate">
                        <th className="py-1">Severity</th>
                        <th className="py-1">Family</th>
                        <th className="py-1">Code</th>
                        <th className="py-1">Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedDiagnostics.issue_summary.normalized_issues.length === 0 && (
                        <tr>
                          <td className="py-2 text-slate" colSpan={4}>
                            no normalized issues
                          </td>
                        </tr>
                      )}
                      {selectedDiagnostics.issue_summary.normalized_issues.map((issue, index) => (
                        <tr className="border-b border-mist/60" key={`${issue.code}-${index}`}>
                          <td className="py-1">{issue.severity || "-"}</td>
                          <td className="py-1">{issue.family || "-"}</td>
                          <td className="py-1">{issue.code || "-"}</td>
                          <td className="py-1">{issue.message || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Repairs</h3>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Applied gap repairs: {selectedDiagnostics.repair_summary.counts.applied_gap_repair_count}</p>
                  <p>Applied duplicate dedupes: {selectedDiagnostics.repair_summary.counts.applied_duplicate_dedupe_count}</p>
                  <p>Skipped source entities: {selectedDiagnostics.repair_summary.counts.skipped_source_entity_count}</p>
                  <p>Remaining unresolved signals: {selectedDiagnostics.repair_summary.counts.remaining_review_required_signal_count}</p>
                </div>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate">
                  <li>Gap repair entries: {selectedDiagnostics.repair_summary.applied_gap_repairs.length}</li>
                  <li>Duplicate dedupe entries: {selectedDiagnostics.repair_summary.applied_duplicate_dedupes.length}</li>
                  <li>Remaining review-required entries: {selectedDiagnostics.repair_summary.remaining_review_required_signals.length}</li>
                </ul>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Acceptance</h3>
                <div className="mt-2 space-y-1 text-xs text-slate">
                  <p>Precedence rule: {selectedDiagnostics.acceptance_summary.precedence_rule_applied || "-"}</p>
                  <p>Outcome: {selectedDiagnostics.acceptance_summary.acceptance_outcome || "-"}</p>
                  <p>
                    Importer highlight: pass=
                    {String((selectedDiagnostics.acceptance_summary.importer_probe.is_pass as boolean | undefined) ?? false)} error=
                    {String((selectedDiagnostics.acceptance_summary.importer_probe.error_code as string | undefined) ?? "-")}
                  </p>
                  <p>
                    Validator highlight: status=
                    {String((selectedDiagnostics.acceptance_summary.validator_probe.status as string | undefined) ?? "-")} pass=
                    {String((selectedDiagnostics.acceptance_summary.validator_probe.is_pass as boolean | undefined) ?? false)}
                  </p>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">Artifacts</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {selectedDiagnostics.artifact_references.length === 0 && <li>no artifact references</li>}
                  {selectedDiagnostics.artifact_references.map((artifact, index) => (
                    <li key={`${artifact.path}-${index}`}>
                      {artifact.download_label || artifact.artifact_kind || "artifact"} | path: {artifact.path || "-"} | exists:{" "}
                      {formatExistsLabel(artifact.exists)}
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
