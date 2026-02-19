import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { Run, RunArtifact, RunLogLine } from "../lib/types";

const TERMINAL_STATUSES = new Set(["done", "failed", "cancelled"]);

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

function statusBadgeClass(status: string): string {
  if (status === "done") {
    return "bg-green-100 text-green-800";
  }
  if (status === "failed" || status === "cancelled") {
    return "bg-red-100 text-red-800";
  }
  if (status === "running") {
    return "bg-amber-100 text-amber-800";
  }
  return "bg-slate-100 text-slate-700";
}

export function RunDetailPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<Run | null>(null);
  const [artifacts, setArtifacts] = useState<RunArtifact[]>([]);
  const [logLines, setLogLines] = useState<RunLogLine[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [downloadingArtifactId, setDownloadingArtifactId] = useState<string | null>(null);
  const [rerunning, setRerunning] = useState(false);

  const nextOffsetRef = useRef(0);

  async function refreshRunData(includeLogs: boolean) {
    if (!projectId || !runId) {
      return;
    }

    try {
      const token = await getAccessToken();
      const [runResponse, artifactResponse] = await Promise.all([api.getRun(token, projectId, runId), api.listRunArtifacts(token, projectId, runId)]);
      setRun(runResponse);
      setArtifacts(artifactResponse.items);

      const shouldPollLog = includeLogs && (runResponse.status === "running" || runResponse.status === "queued");
      if (shouldPollLog) {
        const logResponse = await api.getRunLog(token, projectId, runId, nextOffsetRef.current, 120);
        if (logResponse.lines.length > 0) {
          setLogLines((prev) => [...prev, ...logResponse.lines]);
        }
        nextOffsetRef.current = logResponse.next_offset;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run data refresh failed.");
    }
  }

  useEffect(() => {
    let cancelled = false;
    if (!projectId || !runId) {
      return;
    }

    setLoading(true);
    setError("");
    setLogLines([]);
    nextOffsetRef.current = 0;

    const runOnce = async () => {
      await refreshRunData(true);
      if (!cancelled) {
        setLoading(false);
      }
    };

    void runOnce();

    const timer = window.setInterval(() => {
      if (cancelled) {
        return;
      }
      const shouldPoll = !run || !TERMINAL_STATUSES.has(run.status);
      void refreshRunData(shouldPoll);
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [projectId, runId]);

  const isTerminal = run ? TERMINAL_STATUSES.has(run.status) : false;
  const hasUnplaced = (run?.metrics?.unplaced_count ?? 0) > 0;

  async function handleDownloadArtifact(artifactId: string) {
    if (!projectId || !runId) {
      return;
    }
    setDownloadingArtifactId(artifactId);
    setError("");
    try {
      const token = await getAccessToken();
      const urlResponse = await api.getArtifactUrl(token, projectId, runId, artifactId);
      window.open(urlResponse.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Artifact download failed.");
    } finally {
      setDownloadingArtifactId(null);
    }
  }

  async function handleRerun() {
    if (!projectId || !runId) {
      return;
    }
    setRerunning(true);
    setError("");
    try {
      const token = await getAccessToken();
      const rerunResponse = await api.rerun(token, projectId, runId);
      navigate(`/projects/${projectId}/runs/${rerunResponse.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-run failed.");
    } finally {
      setRerunning(false);
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
          <h1 className="text-2xl font-bold tracking-tight">Run detail</h1>
          <p className="mt-1 text-sm text-slate">Run ID: {runId}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}`}>
            Back to project
          </Link>
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${runId}/export`}>
            Export center
          </Link>
          <Link className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-white" to={`/projects/${projectId}/runs/${runId}/viewer`}>
            Open viewer
          </Link>
        </div>
      </header>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading && <p className="rounded-md border border-mist bg-white px-3 py-2 text-sm text-slate">Loading run state...</p>}

      {run && (
        <article className="rounded-xl border border-mist bg-white p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className={`rounded px-2 py-1 text-sm font-semibold ${statusBadgeClass(run.status)}`}>{run.status.toUpperCase()}</span>
              <span className="text-sm text-slate">Queued: {formatDate(run.queued_at)}</span>
              <span className="text-sm text-slate">Finished: {formatDate(run.finished_at)}</span>
            </div>
            {run.status === "failed" && (
              <button
                className="rounded-md border border-danger/30 px-3 py-2 text-sm font-medium text-danger hover:bg-red-50 disabled:opacity-60"
                disabled={rerunning}
                onClick={() => void handleRerun()}
                type="button"
              >
                {rerunning ? "Re-running..." : "Re-run"}
              </button>
            )}
          </div>

          {hasUnplaced && (
            <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Warning: unplaced parts detected ({run.metrics?.unplaced_count}).
            </p>
          )}

          {run.status === "failed" && run.error_message && (
            <p className="mt-4 rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{run.error_message}</p>
          )}

          {run.status === "done" && run.metrics && (
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-md border border-mist bg-slate-50 p-3 text-sm">
                <p className="text-slate">Sheets</p>
                <p className="text-lg font-semibold text-ink">{run.metrics.sheet_count}</p>
              </div>
              <div className="rounded-md border border-mist bg-slate-50 p-3 text-sm">
                <p className="text-slate">Placed parts</p>
                <p className="text-lg font-semibold text-ink">{run.metrics.placements_count}</p>
              </div>
              <div className="rounded-md border border-mist bg-slate-50 p-3 text-sm">
                <p className="text-slate">Unplaced parts</p>
                <p className="text-lg font-semibold text-ink">{run.metrics.unplaced_count}</p>
              </div>
            </div>
          )}
        </article>
      )}

      <article className="rounded-xl border border-mist bg-white p-5">
        <h2 className="text-lg font-semibold">Run log (polling every 3s while running)</h2>
        <p className="mt-1 text-xs text-slate">Polling automatically slows down after terminal state by skipping log fetches.</p>
        <div className="mt-3 max-h-[280px] overflow-auto rounded-md border border-mist bg-slate-950 p-3 font-mono text-xs text-slate-100">
          {logLines.length === 0 && <p className="text-slate-300">No log lines yet.</p>}
          {logLines.map((line) => (
            <p key={`${line.line_no}-${line.text}`}>
              <span className="text-slate-400">{String(line.line_no).padStart(5, "0")}:</span> {line.text}
            </p>
          ))}
        </div>
      </article>

      <article className="rounded-xl border border-mist bg-white p-5">
        <h2 className="text-lg font-semibold">Artifacts</h2>
        <p className="mt-1 text-xs text-slate">Signed URL download is resolved on-demand from the API.</p>
        {sortedArtifacts.length === 0 && <p className="mt-3 text-sm text-slate">No artifacts available yet.</p>}
        {sortedArtifacts.length > 0 && (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-mist text-left text-slate">
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
                    <td className="py-3">{artifact.filename}</td>
                    <td className="py-3">{artifact.artifact_type}</td>
                    <td className="py-3">{artifact.sheet_index ?? "-"}</td>
                    <td className="py-3">{formatDate(artifact.created_at)}</td>
                    <td className="py-3 text-right">
                      <button
                        className="rounded-md border border-mist px-3 py-1.5 text-slate hover:bg-slate-100 disabled:opacity-60"
                        disabled={downloadingArtifactId === artifact.id}
                        onClick={() => void handleDownloadArtifact(artifact.id)}
                        type="button"
                      >
                        {downloadingArtifactId === artifact.id ? "Loading..." : "Download"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {isTerminal && run?.status !== "done" && (
        <p className="rounded-md border border-mist bg-slate-50 px-3 py-2 text-sm text-slate">
          Terminal state reached: {run?.status.toUpperCase()}. Use re-run if you need a fresh attempt.
        </p>
      )}
    </section>
  );
}
