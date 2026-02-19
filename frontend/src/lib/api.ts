import type {
  ArtifactUrlResponse,
  BundleResponse,
  Project,
  ProjectFile,
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
    return request<ProjectListResponse>("/projects", token, { method: "GET" });
  },

  createProject(token: string, payload: { name: string; description?: string }): Promise<Project> {
    return request<Project>("/projects", token, { method: "POST", body: JSON.stringify(payload) });
  },

  getProject(token: string, projectId: string): Promise<Project> {
    return request<Project>(`/projects/${projectId}`, token, { method: "GET" });
  },

  patchProject(token: string, projectId: string, payload: { name?: string; description?: string }): Promise<Project> {
    return request<Project>(`/projects/${projectId}`, token, { method: "PATCH", body: JSON.stringify(payload) });
  },

  archiveProject(token: string, projectId: string): Promise<void> {
    return request<void>(`/projects/${projectId}`, token, { method: "DELETE" });
  },

  createUploadUrl(
    token: string,
    projectId: string,
    payload: { filename: string; content_type: string; size_bytes: number; file_type: string }
  ): Promise<{ upload_url: string; file_id: string; storage_key: string; expires_at: string }> {
    return request(`/projects/${projectId}/files/upload-url`, token, { method: "POST", body: JSON.stringify(payload) });
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
    }
  ): Promise<ProjectFile> {
    return request<ProjectFile>(`/projects/${projectId}/files`, token, { method: "POST", body: JSON.stringify(payload) });
  },

  listProjectFiles(token: string, projectId: string): Promise<ProjectFileListResponse> {
    return request<ProjectFileListResponse>(`/projects/${projectId}/files`, token, { method: "GET" });
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

  createRun(token: string, projectId: string, payload: { run_config_id: string }): Promise<Run> {
    return request<Run>(`/projects/${projectId}/runs`, token, { method: "POST", body: JSON.stringify(payload) });
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
