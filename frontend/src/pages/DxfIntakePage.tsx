import { useEffect, useMemo, useState } from "react";
import type { DragEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import {
  INTAKE_COPY,
  acceptanceOutcomeBadge,
  issueCountBadge,
  partCreationReadinessBadge,
  recommendedNextStep,
  repairCountBadge,
  runStatusBadge,
} from "../lib/dxfIntakePresentation";
import type {
  PreflightRulesProfileSnapshot,
  PreflightSettingsDraft,
  Project,
  ProjectFile,
  ProjectFileLatestPartCreationProjection,
} from "../lib/types";

interface UploadProgressState {
  total: number;
  done: number;
  status: string;
}

interface PartCreationDraftState {
  code: string;
  name: string;
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
    return "—";
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

function formatExistsLabel(exists: boolean): string {
  return exists ? "yes" : "no";
}

function formatOptionalCount(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? String(Math.max(0, Math.trunc(value))) : INTAKE_COPY.diagnostics.cavity_not_computed;
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

function getPartCreationProjection(file: ProjectFile): ProjectFileLatestPartCreationProjection | null {
  return file.latest_part_creation_projection ?? null;
}

function canCreatePartFromAcceptedFile(file: ProjectFile): boolean {
  const projection = getPartCreationProjection(file);
  if (!projection) {
    return false;
  }
  if (!projection.part_creation_ready || !projection.geometry_revision_id) {
    return false;
  }
  if (projection.existing_part_definition_id || projection.existing_part_revision_id) {
    return false;
  }
  return true;
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
  const [partCreationDraftByFileId, setPartCreationDraftByFileId] = useState<Record<string, PartCreationDraftState>>({});
  const [partCreationStatus, setPartCreationStatus] = useState("");
  const [partCreationError, setPartCreationError] = useState("");
  const [partCreationInFlightFileId, setPartCreationInFlightFileId] = useState<string | null>(null);

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
          include_part_creation_projection: true,
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

  useEffect(() => {
    setPartCreationDraftByFileId((previous) => {
      const next: Record<string, PartCreationDraftState> = { ...previous };
      let changed = false;

      for (const file of files) {
        const projection = getPartCreationProjection(file);
        if (!projection || projection.acceptance_outcome !== "accepted_for_import") {
          continue;
        }
        if (!next[file.id]) {
          next[file.id] = {
            code: projection.suggested_code || "PART",
            name: projection.suggested_name || file.original_filename,
          };
          changed = true;
        }
      }

      for (const fileId of Object.keys(next)) {
        const stillExists = files.some((file) => file.id === fileId);
        if (!stillExists) {
          delete next[fileId];
          changed = true;
        }
      }

      return changed ? next : previous;
    });
  }, [files]);

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

  function handlePartDraftChange(file: ProjectFile, field: "code" | "name", value: string): void {
    const projection = getPartCreationProjection(file);
    setPartCreationDraftByFileId((previous) => {
      const current = previous[file.id] ?? {
        code: projection?.suggested_code || "PART",
        name: projection?.suggested_name || file.original_filename,
      };
      return {
        ...previous,
        [file.id]: {
          ...current,
          [field]: value,
        },
      };
    });
  }

  async function handleCreatePart(file: ProjectFile): Promise<void> {
    if (!projectId || partCreationInFlightFileId) {
      return;
    }
    const projection = getPartCreationProjection(file);
    if (!projection || !canCreatePartFromAcceptedFile(file) || !projection.geometry_revision_id) {
      setPartCreationError("Selected file is not ready for part creation yet.");
      return;
    }

    const draft = partCreationDraftByFileId[file.id] ?? {
      code: projection.suggested_code || "PART",
      name: projection.suggested_name || file.original_filename,
    };
    const code = draft.code.trim();
    const name = draft.name.trim();
    if (!code || !name) {
      setPartCreationError("Part code and name are required.");
      return;
    }

    setPartCreationError("");
    setPartCreationInFlightFileId(file.id);
    setPartCreationStatus(`Creating part from ${file.original_filename}...`);

    try {
      const token = await getAccessToken();
      const created = await api.createProjectPart(token, projectId, {
        code,
        name,
        geometry_revision_id: projection.geometry_revision_id,
        source_label: projection.source_label || file.original_filename,
      });
      setPartCreationStatus(`Created part ${created.code} (revision ${created.revision_no}). Refreshing state...`);
      await loadData();
      setPartCreationStatus(`Created part ${created.code} (revision ${created.revision_no}).`);
    } catch (err) {
      setPartCreationError(err instanceof Error ? err.message : "Part creation failed.");
    } finally {
      setPartCreationInFlightFileId(null);
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
  const selectedCavityObservability =
    selectedDiagnostics?.cavity_observability ?? selectedDiagnosticsFile?.latest_preflight_summary?.cavity_observability ?? null;
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
  const acceptedFilesForParts = useMemo(
    () =>
      files.filter((file) => {
        const projection = getPartCreationProjection(file);
        return projection?.acceptance_outcome === "accepted_for_import";
      }),
    [files]
  );
  const nonAcceptedReviewRequiredCount = useMemo(
    () =>
      files.filter((file) => {
        const projection = getPartCreationProjection(file);
        return projection?.acceptance_outcome === "preflight_review_required";
      }).length,
    [files]
  );
  const nonAcceptedRejectedCount = useMemo(
    () =>
      files.filter((file) => {
        const projection = getPartCreationProjection(file);
        return projection?.acceptance_outcome === "preflight_rejected";
      }).length,
    [files]
  );
  const nonAcceptedPendingCount = useMemo(
    () =>
      files.filter((file) => {
        const projection = getPartCreationProjection(file);
        if (!projection) {
          return false;
        }
        return (
          projection.readiness_reason === "not_eligible_preflight_pending" ||
          projection.readiness_reason === "not_eligible_no_preflight_run"
        );
      }).length,
    [files]
  );

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
            {INTAKE_COPY.page.subtitle(project?.name ?? "Project")}
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
        <>
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header>
              <h2 className="text-lg font-semibold">{INTAKE_COPY.upload.title}</h2>
              <p className="mt-1 text-sm text-slate">
                {INTAKE_COPY.upload.helper}
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
              <p className="text-sm font-medium text-ink">{INTAKE_COPY.upload.dropzone_primary}</p>
              <p className="mt-1 text-xs text-slate">{INTAKE_COPY.upload.dropzone_secondary}</p>
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
              <p className="font-medium text-ink">{INTAKE_COPY.settings.title}</p>
              <p className="mt-1">{INTAKE_COPY.settings.helper}</p>
              <p className="mt-0.5 font-mono text-xs text-slate/70">{INTAKE_COPY.settings.helper_tech}</p>

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
                  {INTAKE_COPY.settings.reset_label}
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
                {INTAKE_COPY.runs.empty}
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
                      <th className="py-2">{INTAKE_COPY.runs.col_next_step}</th>
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
                      const runBadge = runStatusBadge(file);
                      const issueBadge = issueCountBadge(file);
                      const repairBadge = repairCountBadge(file);
                      const acceptanceBadge = acceptanceOutcomeBadge(file);
                      const nextStep = recommendedNextStep(file);
                      const canOpenReview = canOpenConditionalReviewModal(file);
                      return (
                        <tr className="border-b border-mist/70" key={file.id}>
                          <td className="py-3">{file.original_filename}</td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${runBadge.className}`}>
                              {runBadge.label}
                            </span>
                            <p className="mt-1 text-xs text-slate">
                              {summary?.run_seq ? INTAKE_COPY.runs.run_seq(summary.run_seq) : INTAKE_COPY.runs.no_run_yet}
                            </p>
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
                            {nextStep}
                          </td>
                          <td className="py-3">{formatDate(file.latest_preflight_summary?.finished_at ?? null)}</td>
                          <td className="py-3">
                            {canOpenReview ? (
                              <button
                                className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
                                onClick={() => openConditionalReviewModal(file.id)}
                                type="button"
                              >
                                {INTAKE_COPY.runs.cta_open_review}
                              </button>
                            ) : (
                              <span className="text-xs text-slate-400">{INTAKE_COPY.runs.review_na}</span>
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
                              {INTAKE_COPY.runs.cta_view_diagnostics}
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

          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{INTAKE_COPY.acceptedParts.title}</h2>
                <p className="mt-1 text-sm text-slate">
                  {INTAKE_COPY.acceptedParts.helper}
                </p>
              </div>
              <span className="text-sm text-slate">{acceptedFilesForParts.length} accepted files</span>
            </header>

            {(nonAcceptedReviewRequiredCount > 0 || nonAcceptedRejectedCount > 0 || nonAcceptedPendingCount > 0) && (
              <p className="rounded-md border border-mist bg-slate-50 px-3 py-2 text-xs text-slate">
                {INTAKE_COPY.acceptedParts.non_eligible_note(
                  nonAcceptedReviewRequiredCount,
                  nonAcceptedRejectedCount,
                  nonAcceptedPendingCount,
                )}
              </p>
            )}

            {partCreationStatus && (
              <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">{partCreationStatus}</p>
            )}
            {partCreationError && (
              <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{partCreationError}</p>
            )}

            {acceptedFilesForParts.length === 0 && (
              <p className="rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
                {INTAKE_COPY.acceptedParts.empty}
              </p>
            )}

            {acceptedFilesForParts.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-mist text-left text-slate">
                      <th className="py-2">Filename</th>
                      <th className="py-2">Part status</th>
                      <th className="py-2">Geometry revision</th>
                      <th className="py-2">Part code</th>
                      <th className="py-2">Part name</th>
                      <th className="py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {acceptedFilesForParts.map((file) => {
                      const projection = getPartCreationProjection(file);
                      const readiness = partCreationReadinessBadge(file);
                      if (!projection) {
                        return null;
                      }
                      const draft = partCreationDraftByFileId[file.id] ?? {
                        code: projection.suggested_code || "PART",
                        name: projection.suggested_name || file.original_filename,
                      };
                      const canCreate = canCreatePartFromAcceptedFile(file);
                      const disableCreate = !canCreate || partCreationInFlightFileId !== null;

                      return (
                        <tr className="border-b border-mist/70" key={`accepted-part-row-${file.id}`}>
                          <td className="py-3">{file.original_filename}</td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${readiness.className}`}>{readiness.label}</span>
                            <p className="mt-1 text-xs text-slate">{readiness.description}</p>
                          </td>
                          <td className="py-3 text-xs text-slate">
                            {projection.geometry_revision_id || "—"}
                            {projection.geometry_revision_status && (
                              <p className="mt-1">status: {projection.geometry_revision_status}</p>
                            )}
                          </td>
                          <td className="py-3">
                            <input
                              className={`w-full rounded border px-2 py-1 text-xs ${
                                canCreate ? "border-mist bg-white text-ink" : "cursor-not-allowed border-mist/70 bg-slate-100 text-slate-500"
                              }`}
                              disabled={!canCreate}
                              onChange={(event) => handlePartDraftChange(file, "code", event.target.value)}
                              value={draft.code}
                            />
                          </td>
                          <td className="py-3">
                            <input
                              className={`w-full rounded border px-2 py-1 text-xs ${
                                canCreate ? "border-mist bg-white text-ink" : "cursor-not-allowed border-mist/70 bg-slate-100 text-slate-500"
                              }`}
                              disabled={!canCreate}
                              onChange={(event) => handlePartDraftChange(file, "name", event.target.value)}
                              value={draft.name}
                            />
                          </td>
                          <td className="py-3">
                            <button
                              className={`rounded border px-2 py-1 text-xs font-medium ${
                                disableCreate
                                  ? "cursor-not-allowed border-mist/70 bg-slate-100 text-slate-400"
                                  : "border-accent bg-sky-50 text-accent hover:bg-sky-100"
                              }`}
                              disabled={disableCreate}
                              onClick={() => void handleCreatePart(file)}
                              type="button"
                            >
                              {partCreationInFlightFileId === file.id
                                ? INTAKE_COPY.acceptedParts.cta_creating
                                : INTAKE_COPY.acceptedParts.cta_create}
                            </button>
                            {!canCreate && projection.readiness_reason === "accepted_existing_part" && (
                              <p className="mt-1 text-xs text-slate">
                                {INTAKE_COPY.acceptedParts.note_existing_part(
                                  projection.existing_part_code || projection.existing_part_definition_id || "existing definition",
                                )}
                              </p>
                            )}
                            {!canCreate && projection.readiness_reason === "accepted_geometry_import_pending" && (
                              <p className="mt-1 text-xs text-slate">{INTAKE_COPY.acceptedParts.note_geometry_pending}</p>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </>
      )}

      {/* Review required overlay — guidance + replacement upload entry point */}
      {selectedReviewFile && selectedReviewDiagnostics && selectedReviewSummary && canOpenConditionalReviewModal(selectedReviewFile) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl border border-mist bg-white p-5 shadow-xl">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4 border-b border-mist pb-4">
              <div>
                <h2 className="text-xl font-semibold">{INTAKE_COPY.review.overlay_title}</h2>
                <p className="mt-1 text-sm text-slate">{selectedReviewFile.original_filename}</p>
                <p className="mt-0.5 text-xs text-slate">{INTAKE_COPY.review.overlay_subtitle}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-medium ${acceptanceOutcomeBadge(selectedReviewFile).className}`}>
                    {acceptanceOutcomeBadge(selectedReviewFile).label}
                  </span>
                  <span className={`rounded px-2 py-1 text-xs font-medium ${runStatusBadge(selectedReviewFile).className}`}>
                    {runStatusBadge(selectedReviewFile).label}
                  </span>
                  <span className="text-xs text-slate">
                    {selectedReviewSummary.run_seq
                      ? INTAKE_COPY.runs.run_seq(selectedReviewSummary.run_seq)
                      : INTAKE_COPY.runs.review_na}
                  </span>
                  <span className="text-xs text-slate">{formatDate(selectedReviewSummary.finished_at ?? null)}</span>
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
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.review.section_summary}</h3>
                <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                  <p>Review-required issues: {selectedReviewSummary.review_required_issue_count}</p>
                  <p>Remaining review-required signals: {selectedReviewDiagnostics.repair_summary.counts.remaining_review_required_signal_count}</p>
                  <p>Next step: {recommendedNextStep(selectedReviewFile)}</p>
                  <p>Precedence rule: {selectedReviewDiagnostics.acceptance_summary.precedence_rule_applied || "—"}</p>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.review.section_issues}</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {reviewRequiredIssues.length === 0 && <li>{INTAKE_COPY.review.none_label}</li>}
                  {reviewRequiredIssues.map((issue, index) => (
                    <li key={`${issue.code}-${index}`}>
                      [{issue.family || "—"} / {issue.code || "—"}] {issue.message || "—"}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.review.section_signals}</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {remainingReviewSignals.length === 0 && <li>{INTAKE_COPY.review.none_label}</li>}
                  {remainingReviewSignals.map((signal, index) => (
                    <li key={`remaining-review-signal-${index}`}>{formatSignalRecord(signal)}</li>
                  ))}
                </ul>
              </section>

              {/* Guidance — actionable next step */}
              <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-900">{INTAKE_COPY.review.guidance_title}</h3>
                <p className="mt-2 text-sm text-amber-900">{INTAKE_COPY.review.guidance_body}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="rounded border border-mist bg-white px-3 py-1.5 text-xs font-medium text-slate hover:bg-slate-100"
                    onClick={() => {
                      setSelectedDiagnosticsFileId(selectedReviewFile.id);
                      closeConditionalReviewModal();
                    }}
                    type="button"
                  >
                    {INTAKE_COPY.review.cta_open_diagnostics}
                  </button>
                </div>
              </section>

              {/* Technical note — backend/API truth, not actionable guidance */}
              <section className="rounded-lg border border-mist bg-slate-50 p-4">
                <h3 className="text-xs font-semibold text-slate">{INTAKE_COPY.review.tech_note_title}</h3>
                <p className="mt-1 text-xs text-slate">{INTAKE_COPY.review.tech_note_body}</p>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.review.section_replace}</h3>
                <p className="mt-2 text-xs text-slate">{INTAKE_COPY.review.replace_helper}</p>
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
                    {INTAKE_COPY.review.cta_upload_replacement}
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

      {/* Preflight diagnostics drawer — read-only snapshot */}
      {selectedDiagnosticsFile && selectedDiagnostics && (
        <div className="fixed inset-0 z-40 flex justify-end bg-ink/40">
          <div className="h-full w-full max-w-3xl overflow-y-auto border-l border-mist bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-4 border-b border-mist pb-4">
              <div>
                <h2 className="text-xl font-semibold">{INTAKE_COPY.diagnostics.overlay_title}</h2>
                <p className="mt-1 text-sm text-slate">{selectedDiagnosticsFile.original_filename}</p>
                <p className="mt-0.5 text-xs text-slate">{INTAKE_COPY.diagnostics.overlay_subtitle}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className={`rounded px-2 py-1 text-xs font-medium ${runStatusBadge(selectedDiagnosticsFile).className}`}>
                    {runStatusBadge(selectedDiagnosticsFile).label}
                  </span>
                  <span className={`rounded px-2 py-1 text-xs font-medium ${acceptanceOutcomeBadge(selectedDiagnosticsFile).className}`}>
                    {acceptanceOutcomeBadge(selectedDiagnosticsFile).label}
                  </span>
                  <span className="text-xs text-slate">
                    {selectedDiagnosticsFile.latest_preflight_summary?.run_seq
                      ? INTAKE_COPY.runs.run_seq(selectedDiagnosticsFile.latest_preflight_summary.run_seq)
                      : INTAKE_COPY.runs.review_na}
                  </span>
                  <span className="text-xs text-slate">
                    {formatDate(selectedDiagnosticsFile.latest_preflight_summary?.finished_at ?? null)}
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
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_source}</h3>
                <p className="mt-2 text-xs text-slate">
                  Layers: {selectedDiagnostics.source_inventory_summary.found_layers.join(", ") || "—"}
                </p>
                <p className="mt-1 text-xs text-slate">
                  Colors: {selectedDiagnostics.source_inventory_summary.found_colors.join(", ") || "—"}
                </p>
                <p className="mt-1 text-xs text-slate">
                  Linetypes: {selectedDiagnostics.source_inventory_summary.found_linetypes.join(", ") || "—"}
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
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_roles}</h3>
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
                      layer={String(assignment.layer ?? "—")} role={String(assignment.role ?? "—")}
                    </li>
                  ))}
                </ul>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_issues}</h3>
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
                            {INTAKE_COPY.diagnostics.no_issues}
                          </td>
                        </tr>
                      )}
                      {selectedDiagnostics.issue_summary.normalized_issues.map((issue, index) => (
                        <tr className="border-b border-mist/60" key={`${issue.code}-${index}`}>
                          <td className="py-1">{issue.severity || "—"}</td>
                          <td className="py-1">{issue.family || "—"}</td>
                          <td className="py-1">{issue.code || "—"}</td>
                          <td className="py-1">{issue.message || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_repairs}</h3>
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
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_acceptance}</h3>
                <div className="mt-2 space-y-1 text-xs text-slate">
                  <p>Precedence rule: {selectedDiagnostics.acceptance_summary.precedence_rule_applied || "—"}</p>
                  <p>Outcome: {selectedDiagnostics.acceptance_summary.acceptance_outcome || "—"}</p>
                  <p>
                    Importer highlight: pass=
                    {String((selectedDiagnostics.acceptance_summary.importer_probe.is_pass as boolean | undefined) ?? false)} error=
                    {String((selectedDiagnostics.acceptance_summary.importer_probe.error_code as string | undefined) ?? "—")}
                  </p>
                  <p>
                    Validator highlight: status=
                    {String((selectedDiagnostics.acceptance_summary.validator_probe.status as string | undefined) ?? "—")} pass=
                    {String((selectedDiagnostics.acceptance_summary.validator_probe.is_pass as boolean | undefined) ?? false)}
                  </p>
                </div>
              </section>

              {selectedCavityObservability && (
                <section className="rounded-lg border border-mist p-4">
                  <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_cavity}</h3>
                  <div className="mt-2 grid gap-2 text-xs text-slate sm:grid-cols-2">
                    <p>Internal hole count: {selectedCavityObservability.internal_hole_count}</p>
                    <p>Has internal holes: {selectedCavityObservability.has_internal_holes ? "yes" : "no"}</p>
                    <p>Usable cavity candidates: {formatOptionalCount(selectedCavityObservability.usable_cavity_candidate_count)}</p>
                    <p>Too small / invalid cavities: {formatOptionalCount(selectedCavityObservability.too_small_or_invalid_cavity_count)}</p>
                  </div>
                  <p className="mt-2 text-xs text-slate">
                    Basis: {selectedCavityObservability.estimation_basis || INTAKE_COPY.diagnostics.cavity_not_computed}
                  </p>
                </section>
              )}

              <section className="rounded-lg border border-mist p-4">
                <h3 className="text-sm font-semibold text-ink">{INTAKE_COPY.diagnostics.section_artifacts}</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate">
                  {selectedDiagnostics.artifact_references.length === 0 && <li>{INTAKE_COPY.diagnostics.no_artifacts}</li>}
                  {selectedDiagnostics.artifact_references.map((artifact, index) => (
                    <li key={`${artifact.path}-${index}`}>
                      {artifact.download_label || artifact.artifact_kind || "artifact"} | path: {artifact.path || "—"} | exists:{" "}
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
