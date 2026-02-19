import { useEffect, useMemo, useRef, useState } from "react";
import type { DragEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { Project, ProjectFile, Run } from "../lib/types";

type UploadKind = "stock_dxf" | "part_dxf";

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

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const pickerRef = useRef<HTMLInputElement | null>(null);

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [dragActive, setDragActive] = useState(false);
  const [uploadKind, setUploadKind] = useState<UploadKind>("part_dxf");
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState | null>(null);

  async function loadPageData() {
    if (!projectId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const [projectResponse, fileResponse, runResponse] = await Promise.all([
        api.getProject(token, projectId),
        api.listProjectFiles(token, projectId),
        api.listRuns(token, projectId),
      ]);
      setProject(projectResponse);
      setFiles(fileResponse.items);
      setRuns(runResponse.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project details.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPageData();
  }, [projectId]);

  async function handleFilesSelected(fileList: FileList | null) {
    if (!projectId || !fileList || fileList.length === 0) {
      return;
    }
    const selected = Array.from(fileList);
    setUploadProgress({ total: selected.length, done: 0, status: "Preparing upload..." });
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
          file_type: uploadKind,
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
          status: `Finalizing metadata for ${file.name}`,
        });
        await api.completeUpload(token, projectId, {
          file_id: signed.file_id,
          original_filename: file.name,
          storage_key: signed.storage_key,
          file_type: uploadKind,
          size_bytes: file.size,
          content_hash_sha256: null,
        });

        setUploadProgress({
          total: selected.length,
          done: index + 1,
          status: `Uploaded ${file.name}`,
        });
      }

      await loadPageData();
      setUploadProgress({
        total: selected.length,
        done: selected.length,
        status: "Upload complete",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
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

  async function handleDeleteFile(fileId: string) {
    if (!projectId) {
      return;
    }
    setError("");
    try {
      const token = await getAccessToken();
      await api.deleteProjectFile(token, projectId, fileId);
      await loadPageData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete file failed.");
    }
  }

  const uploadPercent = useMemo(() => {
    if (!uploadProgress || uploadProgress.total <= 0) {
      return 0;
    }
    return Math.round((uploadProgress.done / uploadProgress.total) * 100);
  }, [uploadProgress]);

  if (!projectId) {
    return <p className="rounded-md border border-danger/40 bg-red-50 px-4 py-3 text-danger">Missing project id in route.</p>;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{project?.name ?? "Project detail"}</h1>
          <p className="mt-1 text-sm text-slate">{project?.description ?? "Manage files and runs for this project."}</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" onClick={() => void loadPageData()} type="button">
            Refresh
          </button>
          <button className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => navigate(`/projects/${projectId}/new-run`)} type="button">
            New run wizard
          </button>
        </div>
      </div>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading && <p className="rounded-md border border-mist bg-white px-3 py-2 text-sm text-slate">Loading project details...</p>}

      {!loading && (
        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Files</h2>
              <span className="text-sm text-slate">{files.length} items</span>
            </header>

            <div className="grid gap-2 md:grid-cols-[1fr_1fr]">
              <button
                className={`rounded-md border px-3 py-2 text-sm font-medium ${
                  uploadKind === "stock_dxf" ? "border-accent bg-sky-100 text-ink" : "border-mist text-slate"
                }`}
                onClick={() => setUploadKind("stock_dxf")}
                type="button"
              >
                Upload as stock DXF
              </button>
              <button
                className={`rounded-md border px-3 py-2 text-sm font-medium ${
                  uploadKind === "part_dxf" ? "border-accent bg-sky-100 text-ink" : "border-mist text-slate"
                }`}
                onClick={() => setUploadKind("part_dxf")}
                type="button"
              >
                Upload as part DXF
              </button>
            </div>

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
                ref={pickerRef}
                type="file"
              />
              <p className="text-sm font-medium text-ink">Drag and drop DXF files here</p>
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

            {files.length === 0 && <p className="rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">No files uploaded yet.</p>}

            {files.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[680px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-mist text-left text-slate">
                      <th className="py-2">Filename</th>
                      <th className="py-2">Type</th>
                      <th className="py-2">Validation</th>
                      <th className="py-2">Uploaded</th>
                      <th className="py-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((file) => (
                      <tr className="border-b border-mist/70" key={file.id}>
                        <td className="py-3">{file.original_filename}</td>
                        <td className="py-3">{file.file_type}</td>
                        <td className="py-3">
                          <span
                            className={`rounded px-2 py-1 text-xs font-medium ${
                              file.validation_status === "ok"
                                ? "bg-green-100 text-green-800"
                                : file.validation_status === "error"
                                  ? "bg-red-100 text-red-800"
                                  : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {file.validation_status ?? "pending"}
                          </span>
                          {file.validation_error && <p className="mt-1 max-w-[260px] truncate text-xs text-danger">{file.validation_error}</p>}
                        </td>
                        <td className="py-3">{formatDate(file.uploaded_at)}</td>
                        <td className="py-3 text-right">
                          <button
                            className="rounded-md border border-danger/30 px-3 py-1.5 text-danger hover:bg-red-50"
                            onClick={() => void handleDeleteFile(file.id)}
                            type="button"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>

          <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
            <header className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Runs</h2>
              <span className="text-sm text-slate">{runs.length} items</span>
            </header>
            {runs.length === 0 && <p className="rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">No runs yet.</p>}
            {runs.length > 0 && (
              <ul className="space-y-2">
                {runs.map((run) => (
                  <li className="rounded-md border border-mist p-3" key={run.id}>
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">Run {run.id.slice(0, 8)}</p>
                        <p className="text-xs text-slate">Status: {run.status}</p>
                      </div>
                      <Link className="rounded-md border border-mist px-3 py-1.5 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${run.id}`}>
                        Open
                      </Link>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
