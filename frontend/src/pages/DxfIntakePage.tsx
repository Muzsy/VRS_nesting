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

async function uploadFileToSignedUrl(uploadUrl: string, file: File): Promise<void> {
  const putResponse = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });
  if (putResponse.ok) {
    return;
  }

  const postResponse = await fetch(uploadUrl, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });
  if (!postResponse.ok) {
    const body = await postResponse.text();
    throw new Error(body || `Upload failed (${postResponse.status}).`);
  }
}

function formatPreflightStatus(file: ProjectFile): { label: string; className: string } {
  const summary = file.latest_preflight_summary;
  if (!summary) {
    return {
      label: "uploaded / no preflight yet",
      className: "bg-slate-100 text-slate-700",
    };
  }

  if (summary.acceptance_outcome === "accepted_for_import") {
    return {
      label: "accepted_for_import",
      className: "bg-green-100 text-green-800",
    };
  }
  if (summary.acceptance_outcome === "preflight_rejected") {
    return {
      label: "preflight_rejected",
      className: "bg-red-100 text-red-800",
    };
  }
  if (summary.acceptance_outcome === "preflight_review_required") {
    return {
      label: "preflight_review_required",
      className: "bg-amber-100 text-amber-800",
    };
  }

  if (summary.run_status === "preflight_failed") {
    return {
      label: "preflight_failed",
      className: "bg-red-100 text-red-800",
    };
  }

  if (summary.run_status) {
    return {
      label: summary.run_status,
      className: "bg-sky-100 text-sky-800",
    };
  }

  return {
    label: "preflight status unknown",
    className: "bg-slate-100 text-slate-700",
  };
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
        api.listProjectFiles(token, projectId, { include_preflight_summary: true }),
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
        await uploadFileToSignedUrl(signed.upload_url, file);

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

  const uploadPercent = useMemo(() => {
    if (!uploadProgress || uploadProgress.total <= 0) {
      return 0;
    }
    return Math.round((uploadProgress.done / uploadProgress.total) * 100);
  }, [uploadProgress]);

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
              <h2 className="text-lg font-semibold">Latest file preflight status</h2>
              <span className="text-sm text-slate">{files.length} files</span>
            </header>

            {files.length === 0 && (
              <p className="rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
                No files uploaded yet.
              </p>
            )}

            {files.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-mist text-left text-slate">
                      <th className="py-2">Filename</th>
                      <th className="py-2">Type</th>
                      <th className="py-2">Latest preflight</th>
                      <th className="py-2">Finished</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((file) => {
                      const preflightStatus = formatPreflightStatus(file);
                      return (
                        <tr className="border-b border-mist/70" key={file.id}>
                          <td className="py-3">{file.original_filename}</td>
                          <td className="py-3">{file.file_type}</td>
                          <td className="py-3">
                            <span className={`rounded px-2 py-1 text-xs font-medium ${preflightStatus.className}`}>
                              {preflightStatus.label}
                            </span>
                          </td>
                          <td className="py-3">{formatDate(file.latest_preflight_summary?.finished_at ?? null)}</td>
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
    </section>
  );
}
