import type {
  ArtifactUrlResponse,
  BundleResponse,
  PreflightRulesProfileSnapshot,
  Project,
  ProjectFile,
  ProjectFileLatestPreflightSummary,
  ProjectFileListResponse,
  ProjectListResponse,
  Run,
  RunArtifactListResponse,
  RunListResponse,
  RunLogResponse,
  ViewerDataResponse,
} from "./types";

const metaEnv = (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env;
const API_BASE = metaEnv.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000/v1";

function normalizeProject(raw: Record<string, unknown>): Project {
  const ownerIdRaw = raw.owner_id ?? raw.owner_user_id ?? "";
  const lifecycle = String(raw.lifecycle ?? "").trim().toLowerCase();
  return {
    id: String(raw.id ?? ""),
    owner_id: String(ownerIdRaw),
    name: String(raw.name ?? ""),
    description: (raw.description as string | null | undefined) ?? null,
    created_at: (raw.created_at as string | null | undefined) ?? null,
    updated_at: (raw.updated_at as string | null | undefined) ?? null,
    archived_at:
      (raw.archived_at as string | null | undefined) ?? (lifecycle === "archived" ? ((raw.updated_at as string | null | undefined) ?? null) : null),
  };
}

function normalizeUploadFileKind(rawFileType: string): string {
  const value = String(rawFileType || "").trim().toLowerCase();
  if (!value) {
    return "source_dxf";
  }
  if (value === "stock_dxf" || value === "part_dxf") {
    return "source_dxf";
  }
  return value;
}

function normalizeProjectFile(raw: Record<string, unknown>): ProjectFile {
  const fileType = String(raw.file_type ?? raw.file_kind ?? "source_dxf");
  return {
    id: String(raw.id ?? ""),
    project_id: String(raw.project_id ?? ""),
    uploaded_by: String(raw.uploaded_by ?? ""),
    file_type: fileType,
    original_filename: String(raw.original_filename ?? raw.file_name ?? ""),
    storage_key: String(raw.storage_key ?? raw.storage_path ?? ""),
    size_bytes: Number(raw.size_bytes ?? raw.byte_size ?? 0) || null,
    validation_status: (raw.validation_status as string | null | undefined) ?? null,
    validation_error: (raw.validation_error as string | null | undefined) ?? null,
    uploaded_at: (raw.uploaded_at as string | null | undefined) ?? (raw.created_at as string | null | undefined) ?? null,
    latest_preflight_summary: normalizeLatestPreflightSummary(raw.latest_preflight_summary),
  };
}

function normalizeLatestPreflightSummary(raw: unknown): ProjectFileLatestPreflightSummary | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const obj = raw as Record<string, unknown>;
  const runSeqRaw = obj.run_seq;
  const runSeq = typeof runSeqRaw === "number" && Number.isFinite(runSeqRaw) ? runSeqRaw : null;
  const normalizeNonNegativeInt = (value: unknown): number => {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return 0;
    }
    if (value < 0) {
      return 0;
    }
    return Math.trunc(value);
  };

  return {
    preflight_run_id: String(obj.preflight_run_id ?? ""),
    run_seq: runSeq,
    run_status: (obj.run_status as string | null | undefined) ?? null,
    acceptance_outcome: (obj.acceptance_outcome as string | null | undefined) ?? null,
    finished_at: (obj.finished_at as string | null | undefined) ?? null,
    blocking_issue_count: normalizeNonNegativeInt(obj.blocking_issue_count),
    review_required_issue_count: normalizeNonNegativeInt(obj.review_required_issue_count),
    warning_issue_count: normalizeNonNegativeInt(obj.warning_issue_count),
    total_issue_count: normalizeNonNegativeInt(obj.total_issue_count),
    applied_gap_repair_count: normalizeNonNegativeInt(obj.applied_gap_repair_count),
    applied_duplicate_dedupe_count: normalizeNonNegativeInt(obj.applied_duplicate_dedupe_count),
    total_repair_count: normalizeNonNegativeInt(obj.total_repair_count),
    recommended_action: (obj.recommended_action as string | null | undefined) ?? null,
  };
}

async function request<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const headers: HeadersInit = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  listProjects(token: string): Promise<ProjectListResponse> {
    return request<{ items: Array<Record<string, unknown>>; total: number; page: number; page_size: number }>("/projects", token, {
      method: "GET",
    }).then((response) => ({
      ...response,
      items: response.items.map((item) => normalizeProject(item)),
    }));
  },

  createProject(token: string, payload: { name: string; description?: string }): Promise<Project> {
    return request<Record<string, unknown>>("/projects", token, { method: "POST", body: JSON.stringify(payload) }).then((response) =>
      normalizeProject(response)
    );
  },

  getProject(token: string, projectId: string): Promise<Project> {
    return request<Record<string, unknown>>(`/projects/${projectId}`, token, { method: "GET" }).then((response) => normalizeProject(response));
  },

  patchProject(token: string, projectId: string, payload: { name?: string; description?: string }): Promise<Project> {
    return request<Record<string, unknown>>(`/projects/${projectId}`, token, { method: "PATCH", body: JSON.stringify(payload) }).then((response) =>
      normalizeProject(response)
    );
  },

  archiveProject(token: string, projectId: string): Promise<void> {
    return request<void>(`/projects/${projectId}`, token, { method: "DELETE" });
  },

  createUploadUrl(
    token: string,
    projectId: string,
    payload: { filename: string; content_type: string; size_bytes: number; file_type: string }
  ): Promise<{ upload_url: string; file_id: string; storage_key: string; expires_at: string }> {
    return request<{ upload_url: string; file_id: string; storage_key?: string; storage_path?: string; expires_at: string }>(
      `/projects/${projectId}/files/upload-url`,
      token,
      {
        method: "POST",
        body: JSON.stringify({
          filename: payload.filename,
          content_type: payload.content_type,
          size_bytes: payload.size_bytes,
          file_kind: normalizeUploadFileKind(payload.file_type),
        }),
      }
    ).then((response) => ({
      upload_url: response.upload_url,
      file_id: response.file_id,
      storage_key: response.storage_key ?? response.storage_path ?? "",
      expires_at: response.expires_at,
    }));
  },

  completeUpload(
    token: string,
    projectId: string,
    payload: {
      file_id: string;
      original_filename: string;
      storage_key: string;
      file_type: string;
      size_bytes: number;
      content_hash_sha256: string | null;
      rules_profile_snapshot_jsonb?: PreflightRulesProfileSnapshot | null;
    }
  ): Promise<ProjectFile> {
    return request<Record<string, unknown>>(`/projects/${projectId}/files`, token, { method: "POST", body: JSON.stringify(payload) }).then((response) =>
      normalizeProjectFile(response)
    );
  },

  listProjectFiles(
    token: string,
    projectId: string,
    options?: { include_preflight_summary?: boolean }
  ): Promise<ProjectFileListResponse> {
    const includePreflightSummary = options?.include_preflight_summary === true;
    const path = includePreflightSummary
      ? `/projects/${projectId}/files?include_preflight_summary=true`
      : `/projects/${projectId}/files`;
    return request<{ items: Array<Record<string, unknown>>; total: number; page?: number; page_size?: number }>(path, token, {
      method: "GET",
    }).then((response) => ({
      ...response,
      items: response.items.map((item) => normalizeProjectFile(item)),
    }));
  },

  deleteProjectFile(token: string, projectId: string, fileId: string): Promise<void> {
    return request<void>(`/projects/${projectId}/files/${fileId}`, token, { method: "DELETE" });
  },

  listRuns(token: string, projectId: string): Promise<RunListResponse> {
    return request<RunListResponse>(`/projects/${projectId}/runs`, token, { method: "GET" });
  },

  getRun(token: string, projectId: string, runId: string): Promise<Run> {
    return request<Run>(`/projects/${projectId}/runs/${runId}`, token, { method: "GET" });
  },

  createRunConfig(
    token: string,
    projectId: string,
    payload: {
      name: string;
      schema_version: string;
      seed: number;
      time_limit_s: number;
      spacing_mm: number;
      margin_mm: number;
      stock_file_id: string;
      parts_config: Array<{ file_id: string; quantity: number; allowed_rotations_deg: number[] }>;
    }
  ): Promise<{ id: string }> {
    return request<{ id: string }>(`/projects/${projectId}/run-configs`, token, { method: "POST", body: JSON.stringify(payload) });
  },

  listRunConfigs(token: string, projectId: string): Promise<{ items: Array<{ id: string; name?: string | null }>; total: number }> {
    return request<{ items: Array<{ id: string; name?: string | null }>; total: number }>(`/projects/${projectId}/run-configs`, token, { method: "GET" });
  },

  createRun(
    token: string,
    projectId: string,
    payload?: {
      run_config_id?: string;
      idempotency_key?: string;
      run_purpose?: string;
      time_limit_s?: number;
      sa_eval_budget_sec?: number;
    }
  ): Promise<Run> {
    const requestPayload = {
      ...(payload?.idempotency_key ? { idempotency_key: payload.idempotency_key } : {}),
      ...(payload?.run_purpose ? { run_purpose: payload.run_purpose } : {}),
      ...(typeof payload?.time_limit_s === "number" ? { time_limit_s: payload.time_limit_s } : {}),
      ...(typeof payload?.sa_eval_budget_sec === "number" ? { sa_eval_budget_sec: payload.sa_eval_budget_sec } : {}),
    };
    return request<Run>(`/projects/${projectId}/runs`, token, { method: "POST", body: JSON.stringify(requestPayload) });
  },

  rerun(token: string, projectId: string, runId: string): Promise<Run> {
    return request<Run>(`/projects/${projectId}/runs/${runId}/rerun`, token, { method: "POST" });
  },

  cancelRun(token: string, projectId: string, runId: string): Promise<void> {
    return request<void>(`/projects/${projectId}/runs/${runId}`, token, { method: "DELETE" });
  },

  getRunLog(token: string, projectId: string, runId: string, offset: number, lines = 100): Promise<RunLogResponse> {
    return request<RunLogResponse>(`/projects/${projectId}/runs/${runId}/log?offset=${offset}&lines=${lines}`, token, { method: "GET" });
  },

  listRunArtifacts(token: string, projectId: string, runId: string): Promise<RunArtifactListResponse> {
    return request<RunArtifactListResponse>(`/projects/${projectId}/runs/${runId}/artifacts`, token, { method: "GET" });
  },

  getArtifactUrl(token: string, projectId: string, runId: string, artifactId: string): Promise<ArtifactUrlResponse> {
    return request<ArtifactUrlResponse>(`/projects/${projectId}/runs/${runId}/artifacts/${artifactId}/url`, token, { method: "GET" });
  },

  getViewerData(token: string, projectId: string, runId: string): Promise<ViewerDataResponse> {
    return request<ViewerDataResponse>(`/projects/${projectId}/runs/${runId}/viewer-data`, token, { method: "GET" });
  },

  createBundle(token: string, projectId: string, runId: string, artifactIds: string[]): Promise<BundleResponse> {
    return request<BundleResponse>(`/projects/${projectId}/runs/${runId}/artifacts/bundle`, token, {
      method: "POST",
      body: JSON.stringify({ artifact_ids: artifactIds }),
    });
  },

  artifactDownloadPath(projectId: string, runId: string, artifactId: string): string {
    return `${API_BASE}/projects/${projectId}/runs/${runId}/artifacts/${artifactId}/download`;
  },
};
