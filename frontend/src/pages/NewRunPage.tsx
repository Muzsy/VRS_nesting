import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { getAccessToken } from "../lib/supabase";
import type { ProjectFile } from "../lib/types";

type WizardStep = 1 | 2 | 3;

interface PartChoice {
  selected: boolean;
  quantity: number;
  rotationsText: string;
}

function isDxfSourceFile(file: ProjectFile): boolean {
  const fileType = String(file.file_type || "").trim().toLowerCase();
  if (fileType === "source_dxf" || fileType === "part_dxf" || fileType === "stock_dxf") {
    return true;
  }
  const name = String(file.original_filename || "").trim().toLowerCase();
  return name.endsWith(".dxf");
}

function parseRotations(raw: string): number[] {
  const parsed = raw
    .split(",")
    .map((token) => Number.parseInt(token.trim(), 10))
    .filter((value) => Number.isFinite(value));
  const deduped = Array.from(new Set(parsed));
  return deduped.length > 0 ? deduped : [0, 90, 180, 270];
}

export function NewRunPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [step, setStep] = useState<WizardStep>(1);

  const [name, setName] = useState("run-config");
  const [seed, setSeed] = useState(0);
  const [timeLimit, setTimeLimit] = useState(60);
  const [spacing, setSpacing] = useState(2);
  const [margin, setMargin] = useState(5);
  const [stockFileId, setStockFileId] = useState("");
  const [partChoices, setPartChoices] = useState<Record<string, PartChoice>>({});
  const [submitting, setSubmitting] = useState(false);

  async function loadFiles() {
    if (!projectId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const fileResponse = await api.listProjectFiles(token, projectId);
      setFiles(fileResponse.items);

      const choiceMap: Record<string, PartChoice> = {};
      for (const file of fileResponse.items) {
        if (isDxfSourceFile(file)) {
          choiceMap[file.id] = {
            selected: false,
            quantity: 1,
            rotationsText: "0,90,180,270",
          };
        }
      }
      setPartChoices(choiceMap);

      const stockCandidate = fileResponse.items.find((file) => isDxfSourceFile(file)) ?? fileResponse.items[0] ?? null;
      setStockFileId(stockCandidate?.id ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load files for wizard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadFiles();
  }, [projectId]);

  const selectedParts = useMemo(
    () =>
      files
        .filter((file) => partChoices[file.id]?.selected)
        .map((file) => ({
          file_id: file.id,
          quantity: Math.max(1, partChoices[file.id].quantity),
          allowed_rotations_deg: parseRotations(partChoices[file.id].rotationsText),
        })),
    [files, partChoices]
  );

  const canMoveToStep2 = stockFileId.length > 0 && selectedParts.length > 0;

  async function handleSubmitRun() {
    if (!projectId) {
      return;
    }
    if (!canMoveToStep2) {
      setError("Select one stock file and at least one part file.");
      setStep(1);
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const token = await getAccessToken();
      await api.createRunConfig(token, projectId, {
        name: name.trim() || "run-config",
        schema_version: "dxf_v1",
        seed,
        time_limit_s: timeLimit,
        spacing_mm: spacing,
        margin_mm: margin,
        stock_file_id: stockFileId,
        parts_config: selectedParts,
      });
      const run = await api.createRun(token, projectId, { time_limit_s: timeLimit });
      navigate(`/projects/${projectId}/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run creation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!projectId) {
    return <p className="rounded-md border border-danger/40 bg-red-50 px-4 py-3 text-danger">Missing project id in route.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New run wizard</h1>
          <p className="mt-1 text-sm text-slate">3-step flow: files, parameters, summary and run start.</p>
        </div>
        <Link className="rounded-md border border-mist px-3 py-2 text-sm text-slate hover:bg-slate-100" to={`/projects/${projectId}`}>
          Back to project
        </Link>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {[1, 2, 3].map((stepNumber) => (
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              step === stepNumber ? "bg-accent text-white" : "bg-slate-100 text-slate"
            }`}
            key={stepNumber}
          >
            Step {stepNumber}
          </span>
        ))}
      </div>

      {error && <p className="rounded-md border border-danger/40 bg-red-50 px-3 py-2 text-sm text-danger">{error}</p>}
      {loading && <p className="rounded-md border border-mist bg-white px-3 py-2 text-sm text-slate">Loading files...</p>}

      {!loading && step === 1 && (
        <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
          <h2 className="text-lg font-semibold">Step 1: stock + parts</h2>

          <label className="block space-y-1">
            <span className="text-sm font-medium text-slate">Stock file</span>
            <select
              className="w-full rounded-md border border-mist px-3 py-2 outline-none ring-accent focus:ring-2"
              onChange={(event) => setStockFileId(event.target.value)}
              value={stockFileId}
            >
              <option value="">Select stock file</option>
              {files
                .filter((file) => isDxfSourceFile(file))
                .map((file) => (
                  <option key={file.id} value={file.id}>
                    {file.original_filename} ({file.file_type})
                  </option>
                ))}
            </select>
          </label>

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate">Part files</p>
            {files.filter((file) => isDxfSourceFile(file)).length === 0 && (
              <p className="rounded-md border border-dashed border-mist bg-slate-50 px-3 py-2 text-sm text-slate">No DXF source files uploaded yet.</p>
            )}
            {files
              .filter((file) => isDxfSourceFile(file))
              .map((file) => {
                const choice = partChoices[file.id] ?? { selected: false, quantity: 1, rotationsText: "0,90,180,270" };
                return (
                  <div className="grid gap-2 rounded-md border border-mist p-3 md:grid-cols-[auto_1fr_120px_170px]" key={file.id}>
                    <input
                      checked={choice.selected}
                      onChange={(event) =>
                        setPartChoices((prev) => ({
                          ...prev,
                          [file.id]: { ...choice, selected: event.target.checked },
                        }))
                      }
                      type="checkbox"
                    />
                    <span className="text-sm">{file.original_filename}</span>
                    <input
                      className="rounded-md border border-mist px-2 py-1 text-sm"
                      min={1}
                      onChange={(event) =>
                        setPartChoices((prev) => ({
                          ...prev,
                          [file.id]: { ...choice, quantity: Number.parseInt(event.target.value, 10) || 1 },
                        }))
                      }
                      type="number"
                      value={choice.quantity}
                    />
                    <input
                      className="rounded-md border border-mist px-2 py-1 text-sm"
                      onChange={(event) =>
                        setPartChoices((prev) => ({
                          ...prev,
                          [file.id]: { ...choice, rotationsText: event.target.value },
                        }))
                      }
                      placeholder="0,90,180,270"
                      value={choice.rotationsText}
                    />
                  </div>
                );
              })}
          </div>

          <div className="flex justify-end">
            <button
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              disabled={!canMoveToStep2}
              onClick={() => setStep(2)}
              type="button"
            >
              Continue to parameters
            </button>
          </div>
        </article>
      )}

      {!loading && step === 2 && (
        <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
          <h2 className="text-lg font-semibold">Step 2: run parameters</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate">Config name</span>
              <input className="w-full rounded-md border border-mist px-3 py-2" onChange={(event) => setName(event.target.value)} value={name} />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate">Seed</span>
              <input
                className="w-full rounded-md border border-mist px-3 py-2"
                onChange={(event) => setSeed(Number.parseInt(event.target.value, 10) || 0)}
                type="number"
                value={seed}
              />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate">Time limit (s)</span>
              <input
                className="w-full rounded-md border border-mist px-3 py-2"
                max={3600}
                min={1}
                onChange={(event) => setTimeLimit(Math.max(1, Number.parseInt(event.target.value, 10) || 60))}
                type="number"
                value={timeLimit}
              />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate">Spacing (mm)</span>
              <input
                className="w-full rounded-md border border-mist px-3 py-2"
                min={0}
                onChange={(event) => setSpacing(Number.parseFloat(event.target.value) || 0)}
                step="0.1"
                type="number"
                value={spacing}
              />
            </label>
            <label className="space-y-1">
              <span className="text-sm font-medium text-slate">Margin (mm)</span>
              <input
                className="w-full rounded-md border border-mist px-3 py-2"
                min={0}
                onChange={(event) => setMargin(Number.parseFloat(event.target.value) || 0)}
                step="0.1"
                type="number"
                value={margin}
              />
            </label>
          </div>
          <div className="flex justify-between">
            <button className="rounded-md border border-mist px-4 py-2 text-sm text-slate hover:bg-slate-100" onClick={() => setStep(1)} type="button">
              Back
            </button>
            <button className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={() => setStep(3)} type="button">
              Continue to summary
            </button>
          </div>
        </article>
      )}

      {!loading && step === 3 && (
        <article className="space-y-4 rounded-xl border border-mist bg-white p-5">
          <h2 className="text-lg font-semibold">Step 3: summary + start</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <p className="text-sm text-slate">
              <strong className="text-ink">Stock:</strong> {files.find((file) => file.id === stockFileId)?.original_filename ?? "-"}
            </p>
            <p className="text-sm text-slate">
              <strong className="text-ink">Selected parts:</strong> {selectedParts.length}
            </p>
            <p className="text-sm text-slate">
              <strong className="text-ink">Seed:</strong> {seed}
            </p>
            <p className="text-sm text-slate">
              <strong className="text-ink">Time limit:</strong> {timeLimit}s
            </p>
            <p className="text-sm text-slate">
              <strong className="text-ink">Spacing:</strong> {spacing} mm
            </p>
            <p className="text-sm text-slate">
              <strong className="text-ink">Margin:</strong> {margin} mm
            </p>
          </div>
          <div className="flex justify-between">
            <button className="rounded-md border border-mist px-4 py-2 text-sm text-slate hover:bg-slate-100" onClick={() => setStep(2)} type="button">
              Back
            </button>
            <button
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              disabled={submitting}
              onClick={() => void handleSubmitRun()}
              type="button"
            >
              {submitting ? "Starting run..." : "Start run"}
            </button>
          </div>
        </article>
      )}
    </section>
  );
}
