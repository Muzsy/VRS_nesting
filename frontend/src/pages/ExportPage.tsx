import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { RunArtifact } from "../lib/types";

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

export function ExportPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const [artifacts, setArtifacts] = useState<RunArtifact[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bundleUrl, setBundleUrl] = useState("");
  const [bundleName, setBundleName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creatingBundle, setCreatingBundle] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  async function loadArtifacts() {
    if (!projectId || !runId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const response = await api.listRunArtifacts(token, projectId, runId);
      setArtifacts(response.items);
      setSelectedIds(new Set(response.items.map((item) => item.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Artifact loading failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadArtifacts();
  }, [projectId, runId]);

  function toggleSelection(artifactId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) {
        next.delete(artifactId);
      } else {
        next.add(artifactId);
      }
      return next;
    });
  }

  async function handleCreateBundle() {
    if (!projectId || !runId) {
      return;
    }
    if (selectedIds.size === 0) {
      setError("Select at least one artifact.");
      return;
    }

    setCreatingBundle(true);
    setError("");
    setBundleUrl("");
    setBundleName("");
    try {
      const token = await getAccessToken();
      const response = await api.createBundle(token, projectId, runId, Array.from(selectedIds));
      setBundleUrl(response.bundle_url);
      setBundleName(response.filename);
      await loadArtifacts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bundle creation failed.");
    } finally {
      setCreatingBundle(false);
    }
  }

  async function handleDownloadOne(artifactId: string) {
    if (!projectId || !runId) {
      return;
    }
    setDownloadingId(artifactId);
    setError("");
    try {
      const token = await getAccessToken();
      const response = await api.getArtifactUrl(token, projectId, runId, artifactId);
      window.open(response.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Artifact download failed.");
    } finally {
      setDownloadingId(null);
    }
  }

  const sortedArtifacts = useMemo(() => [...artifacts].sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? "")), [artifacts]);

  if (!projectId || !runId) {
    return <p className="rounded-md border border-danger/40 bg-red-50 px-4 py-3 text-danger">Missing project/run id in route.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Export center</h1>
          <p className="mt-1 text-sm text-slate">Select artifacts and create a ZIP bundle, or download items individually.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${runId}`}>
            Back to run detail
          </Link>
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${runId}/viewer`}>
            Open viewer
          </Link>
        </div>
      </header>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}

      <article className="rounded-xl border border-mist bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Artifacts ({artifacts.length})</h2>
          <div className="flex items-center gap-2">
            <button
              className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100"
              onClick={() => setSelectedIds(new Set(artifacts.map((item) => item.id)))}
              type="button"
            >
              Select all
            </button>
            <button className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" onClick={() => setSelectedIds(new Set())} type="button">
              Clear
            </button>
            <button
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              disabled={creatingBundle || selectedIds.size === 0}
              onClick={() => void handleCreateBundle()}
              type="button"
            >
              {creatingBundle ? "Creating ZIP..." : "Create ZIP bundle"}
            </button>
          </div>
        </div>

        {bundleUrl && (
          <p className="mt-4 rounded-md border border-success/40 bg-green-50 px-3 py-2 text-sm text-success">
            Bundle ready:{" "}
            <a className="font-semibold underline" href={bundleUrl} rel="noreferrer" target="_blank">
              {bundleName || "Download ZIP"}
            </a>
          </p>
        )}

        {loading && <p className="mt-3 text-sm text-slate">Loading artifacts...</p>}
        {!loading && sortedArtifacts.length === 0 && <p className="mt-3 rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">No artifacts yet.</p>}

        {!loading && sortedArtifacts.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[800px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-slate">
                  <th className="py-2">Pick</th>
                  <th className="py-2">Filename</th>
                  <th className="py-2">Type</th>
                  <th className="py-2">Sheet</th>
                  <th className="py-2">Created</th>
                  <th className="py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {sortedArtifacts.map((artifact) => (
                  <tr className="border-b border-mist/70" key={artifact.id}>
                    <td className="py-3">
                      <input checked={selectedIds.has(artifact.id)} onChange={() => toggleSelection(artifact.id)} type="checkbox" />
                    </td>
                    <td className="py-3">{artifact.filename}</td>
                    <td className="py-3">{artifact.artifact_type}</td>
                    <td className="py-3">{artifact.sheet_index ?? "-"}</td>
                    <td className="py-3">{formatDate(artifact.created_at)}</td>
                    <td className="py-3 text-right">
                      <button
                        className="rounded-md border border-mist px-3 py-1.5 text-slate hover:bg-slate-100 disabled:opacity-60"
                        disabled={downloadingId === artifact.id}
                        onClick={() => void handleDownloadOne(artifact.id)}
                        type="button"
                      >
                        {downloadingId === artifact.id ? "Loading..." : "Download"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
