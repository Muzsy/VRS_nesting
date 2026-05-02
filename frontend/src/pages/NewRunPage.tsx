import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { projectDetailIntakeStatus } from "../lib/dxfIntakePresentation";
import { getAccessToken } from "../lib/supabase";
import type {
  EngineBackendHint,
  EngineBackendHintMode,
  NestingEngineRuntimePolicy,
  ProjectFile,
  ProjectRunStrategySelection,
  QualityProfileName,
  RunStrategyProfile,
  RunStrategyProfileVersion,
  SolverConfigOverrides,
} from "../lib/types";

type WizardStep = 1 | 2 | 3;
type StrategySource = "project_default" | "choose_profile" | "custom";

interface PartChoice {
  selected: boolean;
  quantity: number;
  rotationsText: string;
}

interface RunStrategyRunPayload {
  run_strategy_profile_version_id?: string;
  quality_profile?: QualityProfileName;
  engine_backend_hint?: EngineBackendHint;
  nesting_engine_runtime_policy?: NestingEngineRuntimePolicy;
  sa_eval_budget_sec?: number;
}

interface CavityPlanMetricsPreview {
  enabled?: boolean;
  version?: string;
  virtual_parent_count?: number;
  internal_placement_count?: number;
  nested_internal_placement_count?: number;
  top_level_holes_removed_count?: number;
  holed_child_proxy_count?: number;
}

interface NewRunLocationState {
  result?: {
    metrics_jsonb?: {
      cavity_plan?: CavityPlanMetricsPreview;
    };
  } | null;
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

function resolveExistingPartRevisionId(file: ProjectFile): string | null {
  const raw = file.latest_part_creation_projection?.existing_part_revision_id;
  if (typeof raw !== "string") {
    return null;
  }
  const cleaned = raw.trim();
  return cleaned.length > 0 ? cleaned : null;
}

const NON_ELIGIBLE_READINESS_REASONS = new Set([
  "not_eligible_rejected",
  "not_eligible_review_required",
  "not_eligible_preflight_pending",
  "not_eligible_no_preflight_run",
]);

function resolveAcceptanceOutcome(file: ProjectFile): string {
  return String(file.latest_part_creation_projection?.acceptance_outcome ?? "")
    .trim()
    .toLowerCase();
}

function resolvePreflightAcceptanceOutcome(file: ProjectFile): string {
  return String(file.latest_preflight_summary?.acceptance_outcome ?? "")
    .trim()
    .toLowerCase();
}

function resolveReadinessReason(file: ProjectFile): string {
  return String(file.latest_part_creation_projection?.readiness_reason ?? "")
    .trim()
    .toLowerCase();
}

function hasAcceptedPreflight(file: ProjectFile): boolean {
  return resolvePreflightAcceptanceOutcome(file) === "accepted_for_import";
}

function hasLinkedPartRevision(file: ProjectFile): boolean {
  return resolveExistingPartRevisionId(file) !== null;
}

function isProjectReadyPartFile(file: ProjectFile): boolean {
  if (!isDxfSourceFile(file)) {
    return false;
  }
  if (!hasAcceptedPreflight(file)) {
    return false;
  }
  if (!file.latest_part_creation_projection || !hasLinkedPartRevision(file)) {
    return false;
  }

  const intakeStatus = projectDetailIntakeStatus(file);
  if (!intakeStatus.isProjectReady || !intakeStatus.isLinkedPart) {
    return false;
  }

  const readinessReason = resolveReadinessReason(file);
  return readinessReason === "accepted_existing_part";
}

function isRunUsableStockFile(file: ProjectFile): boolean {
  if (!isDxfSourceFile(file)) {
    return false;
  }
  if (!hasAcceptedPreflight(file)) {
    return false;
  }

  const projection = file.latest_part_creation_projection;
  if (!projection) {
    return false;
  }

  const intakeStatus = projectDetailIntakeStatus(file);
  if (!intakeStatus.isProjectReady) {
    return false;
  }

  const readinessReason = resolveReadinessReason(file);
  if (NON_ELIGIBLE_READINESS_REASONS.has(readinessReason)) {
    return false;
  }

  const projectionOutcome = resolveAcceptanceOutcome(file);
  if (projectionOutcome === "preflight_rejected" || projectionOutcome === "preflight_review_required") {
    return false;
  }

  const geometryRevisionId = String(projection.geometry_revision_id ?? "").trim();
  return hasLinkedPartRevision(file) || geometryRevisionId.length > 0;
}

function resolvePartRevisionIdForFile(
  file: ProjectFile,
  partRevisionBySourceFileId: Map<string, string>
): string | null {
  const direct = resolveExistingPartRevisionId(file);
  if (direct) {
    return direct;
  }
  const fallback = partRevisionBySourceFileId.get(file.id);
  return fallback ?? null;
}

export function NewRunPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const result = (location.state as NewRunLocationState | null)?.result ?? null;

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

  // Strategy state
  const [strategySource, setStrategySource] = useState<StrategySource>("project_default");
  const [strategyProfiles, setStrategyProfiles] = useState<RunStrategyProfile[]>([]);
  const [strategyVersionsByProfile, setStrategyVersionsByProfile] = useState<Record<string, RunStrategyProfileVersion[]>>({});
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [projectStrategySelection, setProjectStrategySelection] = useState<ProjectRunStrategySelection | null>(null);
  const [strategyLoading, setStrategyLoading] = useState(false);
  const [showCreateProfile, setShowCreateProfile] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [profileCreating, setProfileCreating] = useState(false);
  const [profileCreateError, setProfileCreateError] = useState("");
  // Custom overrides
  const [qualityProfile, setQualityProfile] = useState<QualityProfileName | "">("");
  const [engineBackendHintMode, setEngineBackendHintMode] = useState<EngineBackendHintMode>("auto");
  const [saEvalBudget, setSaEvalBudget] = useState<number | "">("");
  const [placer, setPlacer] = useState<"blf" | "nfp">("nfp");
  const [search, setSearch] = useState<"none" | "sa">("sa");
  const [partInPart, setPartInPart] = useState<"off" | "auto">("off");
  const [compaction, setCompaction] = useState<"off" | "slide">("off");
  const [saIters, setSaIters] = useState<number | "">("");

  async function loadFiles() {
    if (!projectId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = await getAccessToken();
      const fileResponse = await api.listProjectFiles(token, projectId, {
        include_preflight_summary: true,
        include_part_creation_projection: true,
      });
      setFiles(fileResponse.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load files for wizard.");
    } finally {
      setLoading(false);
    }
  }

  async function loadStrategyData() {
    if (!projectId) return;
    setStrategyLoading(true);
    try {
      const token = await getAccessToken();
      const [profiles, selection] = await Promise.all([
        api.listRunStrategyProfiles(token),
        api.getProjectRunStrategySelection(token, projectId),
      ]);
      setStrategyProfiles(profiles);
      setProjectStrategySelection(selection);
    } catch {
      // strategy loading errors are non-fatal; wizard continues with project_default
    } finally {
      setStrategyLoading(false);
    }
  }

  async function handleCreateProfile() {
    if (!newProfileName.trim()) return;
    setProfileCreating(true);
    setProfileCreateError("");
    try {
      const token = await getAccessToken();
      const strategyCode = newProfileName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
      const profile = await api.createRunStrategyProfile(token, {
        strategy_code: strategyCode || "custom_profile",
        display_name: newProfileName.trim(),
      });
      const version = await api.createRunStrategyProfileVersion(token, profile.id, { is_active: true });
      setStrategyProfiles((prev) => [...prev, profile]);
      setStrategyVersionsByProfile((prev) => ({ ...prev, [profile.id]: [version] }));
      setSelectedProfileId(profile.id);
      setSelectedVersionId(version.id);
      setNewProfileName("");
      setShowCreateProfile(false);
    } catch (err) {
      setProfileCreateError(err instanceof Error ? err.message : "Profile creation failed.");
    } finally {
      setProfileCreating(false);
    }
  }

  async function loadProfileVersions(profileId: string) {
    if (!profileId) return;
    try {
      const token = await getAccessToken();
      const versions = await api.listRunStrategyProfileVersions(token, profileId);
      setStrategyVersionsByProfile((prev) => ({ ...prev, [profileId]: versions }));
      const activeVersion = versions.find((v) => v.is_active) ?? versions[0];
      setSelectedVersionId(activeVersion?.id ?? "");
    } catch {
      // non-fatal
    }
  }

  useEffect(() => {
    void loadFiles();
  }, [projectId]);

  useEffect(() => {
    void loadStrategyData();
  }, [projectId]);

  const dxfSourceFiles = useMemo(() => files.filter(isDxfSourceFile), [files]);

  const projectReadyPartFiles = useMemo(() => dxfSourceFiles.filter((file) => isProjectReadyPartFile(file)), [dxfSourceFiles]);

  const eligibleStockFiles = useMemo(() => dxfSourceFiles.filter((file) => isRunUsableStockFile(file)), [dxfSourceFiles]);

  const intakeAttentionFiles = useMemo(() => dxfSourceFiles.filter((file) => !isProjectReadyPartFile(file)), [dxfSourceFiles]);

  useEffect(() => {
    setPartChoices((prev) => {
      const next: Record<string, PartChoice> = {};
      for (const file of projectReadyPartFiles) {
        const existing = prev[file.id];
        next[file.id] = {
          selected: existing?.selected ?? false,
          quantity: Math.max(1, existing?.quantity ?? 1),
          rotationsText: existing?.rotationsText ?? "0,90,180,270",
        };
      }
      return next;
    });
  }, [projectReadyPartFiles]);

  useEffect(() => {
    setStockFileId((currentStockFileId) => {
      if (eligibleStockFiles.some((file) => file.id === currentStockFileId)) {
        return currentStockFileId;
      }
      return eligibleStockFiles[0]?.id ?? "";
    });
  }, [eligibleStockFiles]);

  const selectedParts = useMemo(
    () =>
      projectReadyPartFiles
        .filter((file) => partChoices[file.id]?.selected)
        .map((file) => ({
          file_id: file.id,
          quantity: Math.max(1, partChoices[file.id].quantity),
          allowed_rotations_deg: parseRotations(partChoices[file.id].rotationsText),
        })),
    [projectReadyPartFiles, partChoices]
  );

  const filesById = useMemo(() => {
    const byId = new Map<string, ProjectFile>();
    for (const file of files) {
      byId.set(file.id, file);
    }
    return byId;
  }, [files]);

  const canMoveToStep2 = stockFileId.length > 0 && selectedParts.length > 0;

  function buildNestingRuntimePolicy(): NestingEngineRuntimePolicy {
    const policy: NestingEngineRuntimePolicy = { placer, search, part_in_part: partInPart, compaction };
    if (search === "sa" && typeof saIters === "number" && saIters > 0) {
      policy.sa_iters = saIters;
    }
    return policy;
  }

  function buildSolverConfigOverrides(): SolverConfigOverrides {
    const overrides: SolverConfigOverrides = { nesting_engine_runtime_policy: buildNestingRuntimePolicy() };
    if (qualityProfile) overrides.quality_profile = qualityProfile;
    if (engineBackendHintMode !== "auto") overrides.engine_backend_hint = engineBackendHintMode;
    if (typeof saEvalBudget === "number" && saEvalBudget > 0) overrides.sa_eval_budget_sec = saEvalBudget;
    return overrides;
  }

  function buildRunStrategyRequestPayload(): RunStrategyRunPayload {
    if (strategySource === "project_default") return {};
    if (strategySource === "choose_profile") {
      return selectedVersionId ? { run_strategy_profile_version_id: selectedVersionId } : {};
    }
    // custom
    const payload: RunStrategyRunPayload = {};
    if (selectedVersionId) payload.run_strategy_profile_version_id = selectedVersionId;
    if (qualityProfile) payload.quality_profile = qualityProfile;
    if (engineBackendHintMode !== "auto") payload.engine_backend_hint = engineBackendHintMode;
    if (typeof saEvalBudget === "number" && saEvalBudget > 0) payload.sa_eval_budget_sec = saEvalBudget;
    payload.nesting_engine_runtime_policy = buildNestingRuntimePolicy();
    return payload;
  }

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

      const runConfig = await api.createRunConfig(token, projectId, {
        name: name.trim() || "run-config",
        schema_version: "dxf_v1",
        seed,
        time_limit_s: timeLimit,
        spacing_mm: spacing,
        margin_mm: margin,
        stock_file_id: stockFileId,
        parts_config: selectedParts,
        ...(strategySource !== "project_default" && selectedVersionId ? { run_strategy_profile_version_id: selectedVersionId } : {}),
        ...(strategySource === "custom" ? { solver_config_overrides_jsonb: buildSolverConfigOverrides() } : {}),
      });

      // Keep snapshot source of truth in sync with wizard quantities.
      const requirements = await api.listProjectPartRequirements(token, projectId);
      const requirementsByRevisionId = new Map(requirements.items.map((item) => [item.part_revision_id, item]));
      const partRevisionBySourceFileId = new Map(
        requirements.items
          .map((item) => [String(item.source_file_object_id || "").trim(), item.part_revision_id] as const)
          .filter(([sourceFileId, partRevisionId]) => sourceFileId.length > 0 && String(partRevisionId || "").trim().length > 0)
      );

      const wizardRevisionIds = new Set<string>();
      const selectedRevisionIds = new Set<string>();

      for (const file of projectReadyPartFiles) {
        const revisionId = resolvePartRevisionIdForFile(file, partRevisionBySourceFileId);
        if (revisionId) {
          wizardRevisionIds.add(revisionId);
        }
      }

      for (const selected of selectedParts) {
        const sourceFile = filesById.get(selected.file_id);
        if (!sourceFile) {
          throw new Error(`Selected file not found: ${selected.file_id}`);
        }
        const partRevisionId = resolvePartRevisionIdForFile(sourceFile, partRevisionBySourceFileId);
        if (!partRevisionId) {
          throw new Error(`Selected file has no linked part revision: ${sourceFile.original_filename}`);
        }
        const existing = requirementsByRevisionId.get(partRevisionId);
        await api.upsertProjectPartRequirement(token, projectId, {
          part_revision_id: partRevisionId,
          required_qty: Math.max(1, selected.quantity),
          placement_priority: existing?.placement_priority ?? 50,
          placement_policy: existing?.placement_policy ?? "normal",
          is_active: true,
          ...(existing?.notes ? { notes: existing.notes } : {}),
        });
        selectedRevisionIds.add(partRevisionId);
      }

      // Reflect wizard selection: mapped-but-unselected parts are deactivated.
      for (const requirement of requirements.items) {
        if (!wizardRevisionIds.has(requirement.part_revision_id)) {
          continue;
        }
        if (selectedRevisionIds.has(requirement.part_revision_id)) {
          continue;
        }
        if (!requirement.is_active) {
          continue;
        }
        await api.upsertProjectPartRequirement(token, projectId, {
          part_revision_id: requirement.part_revision_id,
          required_qty: Math.max(1, requirement.required_qty),
          placement_priority: requirement.placement_priority,
          placement_policy: requirement.placement_policy,
          is_active: false,
          ...(requirement.notes ? { notes: requirement.notes } : {}),
        });
      }

      const run = await api.createRun(token, projectId, {
        run_config_id: runConfig.id,
        time_limit_s: timeLimit,
        ...buildRunStrategyRequestPayload(),
      });
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

  const strategySummaryLabel =
    strategySource === "project_default"
      ? projectStrategySelection
        ? `Project default (v${projectStrategySelection.version_no ?? "?"})`
        : "Project default (global fallback)"
      : strategySource === "choose_profile"
      ? selectedVersionId
        ? `Profile version: ${selectedVersionId.slice(0, 8)}…`
        : "Choose profile (no version selected)"
      : [
          "Custom",
          qualityProfile ? `quality=${qualityProfile}` : null,
          engineBackendHintMode !== "auto" ? `engine=${engineBackendHintMode}` : "engine=auto",
          typeof saEvalBudget === "number" && saEvalBudget > 0 ? `sa_budget=${saEvalBudget}s` : null,
        ]
          .filter(Boolean)
          .join(", ");

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
              {eligibleStockFiles.map((file) => (
                <option key={file.id} value={file.id}>
                  {file.original_filename} ({file.file_type})
                </option>
              ))}
            </select>
          </label>

          <div className="space-y-2">
            <p className="text-sm font-medium text-slate">Part files</p>
            {projectReadyPartFiles.length === 0 && (
              <div className="space-y-2 rounded-md border border-dashed border-mist bg-slate-50 px-3 py-3 text-sm text-slate">
                <p>No project-ready parts yet. Open DXF Intake / Project Preparation and create parts first.</p>
                <Link className="font-medium text-accent underline" to={`/projects/${projectId}/dxf-intake`}>
                  Open DXF Intake / Project Preparation
                </Link>
                {dxfSourceFiles.length > 0 && (
                  <p className="text-xs text-slate">
                    {intakeAttentionFiles.length} source file(s) are currently not eligible for part selection in this wizard.
                  </p>
                )}
              </div>
            )}
            {projectReadyPartFiles.map((file) => {
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

          {/* Strategy section */}
          <div className="space-y-3 rounded-md border border-mist p-4">
            <p className="text-sm font-semibold text-ink">Nesting strategy</p>
            {strategyLoading ? (
              <p className="text-sm text-slate">Loading strategy data...</p>
            ) : (
              <>
                <div className="flex flex-wrap gap-5" role="radiogroup" aria-label="Strategy source">
                  {(["project_default", "choose_profile", "custom"] as StrategySource[]).map((src) => (
                    <label key={src} className="flex cursor-pointer items-center gap-2 text-sm">
                      <input
                        checked={strategySource === src}
                        name="strategySource"
                        onChange={() => setStrategySource(src)}
                        type="radio"
                        value={src}
                      />
                      {src === "project_default" ? "Project default" : src === "choose_profile" ? "Choose profile" : "Custom overrides"}
                    </label>
                  ))}
                </div>

                {strategySource === "project_default" && (
                  <p className="text-xs text-slate">
                    {projectStrategySelection
                      ? `Project default: profile version ${projectStrategySelection.active_run_strategy_profile_version_id.slice(0, 8)}…`
                      : "No project default strategy selected — global default will be used."}
                  </p>
                )}

                {(strategySource === "choose_profile" || strategySource === "custom") && (
                  <div className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-2">
                      <label className="space-y-1">
                        <span className="text-xs font-medium text-slate">Profile</span>
                        <select
                          aria-label="Strategy profile"
                          className="w-full rounded-md border border-mist px-3 py-2 text-sm"
                          disabled={strategyProfiles.length === 0}
                          onChange={(e) => {
                            setSelectedProfileId(e.target.value);
                            void loadProfileVersions(e.target.value);
                          }}
                          value={selectedProfileId}
                        >
                          <option value="">{strategyProfiles.length === 0 ? "No profiles yet" : "Select profile…"}</option>
                          {strategyProfiles.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.display_name}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="space-y-1">
                        <span className="text-xs font-medium text-slate">Version</span>
                        <select
                          aria-label="Strategy version"
                          className="w-full rounded-md border border-mist px-3 py-2 text-sm"
                          disabled={!selectedProfileId || (strategyVersionsByProfile[selectedProfileId] ?? []).length === 0}
                          onChange={(e) => setSelectedVersionId(e.target.value)}
                          value={selectedVersionId}
                        >
                          <option value="">Select version…</option>
                          {(strategyVersionsByProfile[selectedProfileId] ?? []).map((v) => (
                            <option key={v.id} value={v.id}>
                              v{v.version_no}
                              {v.is_active ? " (active)" : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>

                    {strategySource === "choose_profile" && (
                      <div>
                        {!showCreateProfile ? (
                          <button
                            className="text-xs text-accent underline hover:no-underline"
                            onClick={() => setShowCreateProfile(true)}
                            type="button"
                          >
                            + Create new profile
                          </button>
                        ) : (
                          <div className="space-y-2 rounded-md border border-mist bg-slate-50 p-3">
                            <p className="text-xs font-medium text-slate">New profile</p>
                            <div className="flex gap-2">
                              <input
                                autoFocus
                                className="flex-1 rounded-md border border-mist bg-white px-3 py-1.5 text-sm"
                                onChange={(e) => setNewProfileName(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter") void handleCreateProfile(); if (e.key === "Escape") setShowCreateProfile(false); }}
                                placeholder="Profile display name…"
                                value={newProfileName}
                              />
                              <button
                                className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
                                disabled={profileCreating || !newProfileName.trim()}
                                onClick={() => void handleCreateProfile()}
                                type="button"
                              >
                                {profileCreating ? "Creating…" : "Create"}
                              </button>
                              <button
                                className="rounded-md border border-mist px-3 py-1.5 text-sm text-slate hover:bg-slate-100"
                                onClick={() => { setShowCreateProfile(false); setProfileCreateError(""); }}
                                type="button"
                              >
                                Cancel
                              </button>
                            </div>
                            {profileCreateError && <p className="text-xs text-danger">{profileCreateError}</p>}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {strategySource === "custom" && (
                  <div className="grid gap-3 rounded-md border border-mist bg-slate-50 p-3 md:grid-cols-2">
                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Quality profile</span>
                      <select
                        aria-label="Quality profile"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setQualityProfile(e.target.value as QualityProfileName | "")}
                        value={qualityProfile}
                      >
                        <option value="">Default</option>
                        <option value="fast_preview">Fast preview</option>
                        <option value="quality_default">Quality default</option>
                        <option value="quality_aggressive">Quality aggressive</option>
                        <option value="quality_cavity_prepack">Quality cavity prepack</option>
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Engine backend</span>
                      <select
                        aria-label="Engine backend"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setEngineBackendHintMode(e.target.value as EngineBackendHintMode)}
                        value={engineBackendHintMode}
                      >
                        <option value="auto">Auto (resolver default)</option>
                        <option value="sparrow_v1">Sparrow v1</option>
                        <option value="nesting_engine_v2">Nesting Engine v2</option>
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">SA eval budget (s)</span>
                      <input
                        aria-label="SA eval budget (s)"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        min={0}
                        onChange={(e) => setSaEvalBudget(e.target.value ? Number.parseFloat(e.target.value) : "")}
                        step="0.5"
                        type="number"
                        value={saEvalBudget}
                      />
                    </label>

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Placer</span>
                      <select
                        aria-label="Placer"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setPlacer(e.target.value as "blf" | "nfp")}
                        value={placer}
                      >
                        <option value="nfp">NFP</option>
                        <option value="blf">BLF</option>
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Search</span>
                      <select
                        aria-label="Search"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setSearch(e.target.value as "none" | "sa")}
                        value={search}
                      >
                        <option value="sa">SA (simulated annealing)</option>
                        <option value="none">None</option>
                      </select>
                    </label>

                    {search === "sa" && (
                      <label className="space-y-1">
                        <span className="text-xs font-medium text-slate">SA iterations</span>
                        <input
                          aria-label="SA iterations"
                          className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                          min={1}
                          onChange={(e) => setSaIters(e.target.value ? Number.parseInt(e.target.value, 10) : "")}
                          type="number"
                          value={saIters}
                        />
                      </label>
                    )}

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Part in part</span>
                      <select
                        aria-label="Part in part"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setPartInPart(e.target.value as "off" | "auto")}
                        value={partInPart}
                      >
                        <option value="off">Off</option>
                        <option value="auto">Auto</option>
                      </select>
                    </label>

                    <label className="space-y-1">
                      <span className="text-xs font-medium text-slate">Compaction</span>
                      <select
                        aria-label="Compaction"
                        className="w-full rounded-md border border-mist bg-white px-3 py-2 text-sm"
                        onChange={(e) => setCompaction(e.target.value as "off" | "slide")}
                        value={compaction}
                      >
                        <option value="off">Off</option>
                        <option value="slide">Slide</option>
                      </select>
                    </label>
                  </div>
                )}
              </>
            )}
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
            <p className="col-span-2 text-sm text-slate">
              <strong className="text-ink">Strategy:</strong> {strategySummaryLabel}
            </p>
          </div>
          {result?.metrics_jsonb?.cavity_plan?.enabled && (
            <div className="rounded-lg border border-mist bg-slate-50 p-4">
              <h4 className="text-sm font-semibold text-ink">Cavity prepack összefoglaló</h4>
              <ul className="mt-2 space-y-1 text-sm text-slate">
                <li>Verzió: {result.metrics_jsonb.cavity_plan.version ?? "n/a"}</li>
                <li>Virtuális parentek: {result.metrics_jsonb.cavity_plan.virtual_parent_count ?? 0}</li>
                <li>Belső elhelyezések: {result.metrics_jsonb.cavity_plan.internal_placement_count ?? 0}</li>
                <li>Matrjoska (≥2. szint): {result.metrics_jsonb.cavity_plan.nested_internal_placement_count ?? 0}</li>
                <li>Top-level solver holes eltávolítva: {result.metrics_jsonb.cavity_plan.top_level_holes_removed_count ?? 0}</li>
                <li>Lyukas child proxy: {result.metrics_jsonb.cavity_plan.holed_child_proxy_count ?? 0}</li>
              </ul>
            </div>
          )}
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
