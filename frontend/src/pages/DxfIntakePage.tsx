import { useEffect, useMemo, useState } from "react";
import type { DragEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { Project, ProjectFile } from "../lib/types";

interface UploadProgressState {
  total: number;
  done: number;
  status: string;
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
              <p className="font-medium text-ink">Current defaults (read-only in E4-T1)</p>
              <p className="mt-1">Rules profile/settings editor arrives in E4-T2. This page currently uses backend defaults.</p>
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
