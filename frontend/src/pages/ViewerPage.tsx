import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ViewerCanvas } from "../components/ViewerCanvas";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { ViewerDataResponse } from "../lib/types";

function formatExpires(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString();
}

export function ViewerPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const [viewerData, setViewerData] = useState<ViewerDataResponse | null>(null);
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadViewerData(options?: { resetSheet?: boolean; silent?: boolean }) {
    if (!projectId || !runId) {
      return;
    }

    const resetSheet = options?.resetSheet ?? false;
    const silent = options?.silent ?? false;

    if (!silent) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const token = await getAccessToken();
      const response = await api.getViewerData(token, projectId, runId);
      setViewerData(response);

      if (resetSheet) {
        setActiveSheetIndex(0);
      } else {
        setActiveSheetIndex((previous) => {
          if (response.sheets.length === 0) {
            return 0;
          }
          return Math.min(previous, response.sheets.length - 1);
        });
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Viewer data loading failed.");
    } finally {
      if (!silent) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }

  useEffect(() => {
    if (!projectId || !runId) {
      return;
    }

    let cancelled = false;
    (async () => {
      if (cancelled) {
        return;
      }
      await loadViewerData({ resetSheet: true, silent: false });
    })();

    const refreshTimer = window.setInterval(() => {
      if (cancelled) {
        return;
      }
      void loadViewerData({ resetSheet: false, silent: true });
    }, 240000);

    return () => {
      cancelled = true;
      window.clearInterval(refreshTimer);
    };
  }, [projectId, runId]);

  const sheets = viewerData?.sheets ?? [];
  const activeSheet = sheets[activeSheetIndex] ?? null;

  const activeSheetPlacements = useMemo(() => {
    if (!viewerData || !activeSheet) {
      return [];
    }
    return viewerData.placements.filter((item) => item.sheet_index === activeSheet.sheet_index);
  }, [viewerData, activeSheet]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (sheets.length <= 1) {
        return;
      }
      if (event.key === "ArrowRight") {
        setActiveSheetIndex((prev) => (prev + 1) % sheets.length);
      } else if (event.key === "ArrowLeft") {
        setActiveSheetIndex((prev) => (prev - 1 + sheets.length) % sheets.length);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [sheets.length]);

  if (!projectId || !runId) {
    return <p className="rounded-md border border-danger/40 bg-red-50 px-4 py-3 text-danger">Missing project/run id in route.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Layout viewer</h1>
          <p className="mt-1 text-sm text-slate">Pan/zoom + hover tooltip + click detail + multi-sheet navigation.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${runId}`}>
            Back to run detail
          </Link>
          <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}/runs/${runId}/export`}>
            Export center
          </Link>
          <button
            className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100"
            onClick={() => void loadViewerData({ resetSheet: false, silent: false })}
            type="button"
          >
            Refresh viewer data
          </button>
        </div>
      </header>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading && <p className="rounded-md border border-mist bg-white px-3 py-2 text-sm text-slate">Loading viewer data...</p>}

      {!loading && viewerData && (
        <>
          <article className="rounded-xl border border-mist bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-slate">
                <span className="rounded bg-slate-100 px-2 py-1">status: {viewerData.status}</span>
                <span className="rounded bg-slate-100 px-2 py-1">sheet_count: {viewerData.sheet_count}</span>
                <span className="rounded bg-slate-100 px-2 py-1">placements: {viewerData.placements.length}</span>
                {refreshing && <span className="rounded bg-slate-100 px-2 py-1">refreshing signed URLs...</span>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100 disabled:opacity-60"
                  disabled={sheets.length <= 1}
                  onClick={() => setActiveSheetIndex((prev) => (prev - 1 + sheets.length) % sheets.length)}
                  type="button"
                >
                  Prev sheet
                </button>
                <button
                  className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100 disabled:opacity-60"
                  disabled={sheets.length <= 1}
                  onClick={() => setActiveSheetIndex((prev) => (prev + 1) % sheets.length)}
                  type="button"
                >
                  Next sheet
                </button>
              </div>
            </div>

            {activeSheet && (
              <div className="mt-3 grid gap-2 rounded-md border border-mist bg-slate-50 p-3 text-xs text-slate md:grid-cols-5">
                <p>sheet: {activeSheet.sheet_index + 1}</p>
                <p>
                  size: {activeSheet.width_mm?.toFixed(1) ?? "-"} x {activeSheet.height_mm?.toFixed(1) ?? "-"} mm
                </p>
                <p>placements: {activeSheet.placements_count}</p>
                <p>utilization: {activeSheet.utilization_pct?.toFixed(2) ?? "-"}%</p>
                <p>svg url exp: {formatExpires(activeSheet.svg_url_expires_at)}</p>
              </div>
            )}

            {activeSheet ? (
              <div className="mt-4">
                <ViewerCanvas
                  onSvgError={() => {
                    void loadViewerData({ resetSheet: false, silent: true });
                  }}
                  placements={activeSheetPlacements}
                  sheetIndex={activeSheet.sheet_index}
                  svgUrl={activeSheet.svg_url ?? null}
                />
              </div>
            ) : (
              <p className="mt-4 rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
                No sheet artifacts found. Viewer fallback uses solver placements.
              </p>
            )}
          </article>

          {viewerData.unplaced.length > 0 && (
            <article className="rounded-xl border border-amber-300 bg-amber-50 p-5">
              <h2 className="text-lg font-semibold text-amber-800">Unplaced parts</h2>
              <p className="mt-1 text-sm text-amber-800">Total: {viewerData.unplaced.length}</p>
              <ul className="mt-3 grid gap-2 md:grid-cols-2">
                {viewerData.unplaced.slice(0, 40).map((item) => (
                  <li className="rounded border border-amber-200 bg-white px-3 py-2 text-sm text-amber-900" key={item.instance_id}>
                    {item.part_id} ({item.instance_id}) {item.reason ? `- ${item.reason}` : ""}
                  </li>
                ))}
              </ul>
            </article>
          )}
        </>
      )}
    </section>
  );
}
