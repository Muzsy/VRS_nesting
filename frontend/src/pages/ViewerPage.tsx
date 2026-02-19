import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ViewerCanvas } from "../components/ViewerCanvas";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { ViewerDataResponse } from "../lib/types";

export function ViewerPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const [viewerData, setViewerData] = useState<ViewerDataResponse | null>(null);
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);
  const [signedSvgUrls, setSignedSvgUrls] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!projectId || !runId) {
      return;
    }

    async function loadViewerData() {
      if (!projectId || !runId) {
        return;
      }
      const currentProjectId = projectId;
      const currentRunId = runId;

      setLoading(true);
      setError("");
      try {
        const token = await getAccessToken();
        const response = await api.getViewerData(token, currentProjectId, currentRunId);
        if (cancelled) {
          return;
        }
        setViewerData(response);
        setActiveSheetIndex(0);

        const signedMap: Record<string, string> = {};
        for (const sheet of response.sheets) {
          if (!sheet.svg_artifact_id) {
            continue;
          }
          try {
            const signed = await api.getArtifactUrl(token, currentProjectId, currentRunId, sheet.svg_artifact_id);
            signedMap[sheet.svg_artifact_id] = signed.download_url;
          } catch {
            signedMap[sheet.svg_artifact_id] = "";
          }
        }
        if (!cancelled) {
          setSignedSvgUrls(signedMap);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Viewer data loading failed.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadViewerData();
    return () => {
      cancelled = true;
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

            {activeSheet ? (
              <div className="mt-4">
                <ViewerCanvas
                  placements={activeSheetPlacements}
                  sheetIndex={activeSheet.sheet_index}
                  svgUrl={activeSheet.svg_artifact_id ? signedSvgUrls[activeSheet.svg_artifact_id] || null : null}
                />
              </div>
            ) : (
              <p className="mt-4 rounded-md border border-dashed border-mist bg-slate-50 px-4 py-3 text-sm text-slate">
                No sheet artifacts found. Viewer fallback can still use placement points if available.
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
