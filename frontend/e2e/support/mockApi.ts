import type { Page, Route } from "@playwright/test";

type RunStatus = "queued" | "running" | "done" | "failed" | "cancelled";

interface MockProject {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

interface MockFile {
  id: string;
  project_id: string;
  uploaded_by: string;
  file_type: string;
  original_filename: string;
  storage_key: string;
  validation_status: string;
  validation_error: string | null;
  uploaded_at: string;
  latest_preflight_summary?: Record<string, unknown> | null;
  latest_preflight_diagnostics?: Record<string, unknown> | null;
  latest_part_creation_projection?: Record<string, unknown> | null;
}

interface MockRun {
  id: string;
  project_id: string;
  run_config_id: string;
  triggered_by: string;
  status: RunStatus;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_sec: number | null;
  solver_exit_code: number | null;
  error_message: string | null;
  metrics: { placements_count: number; unplaced_count: number; sheet_count: number } | null;
}

interface MockArtifact {
  id: string;
  run_id: string;
  artifact_type: string;
  filename: string;
  storage_key: string;
  size_bytes: number;
  sheet_index: number | null;
  created_at: string;
}

interface ViewerSheet {
  sheet_index: number;
  dxf_artifact_id: string | null;
  svg_artifact_id: string | null;
  dxf_filename: string | null;
  svg_filename: string | null;
  dxf_download_path: string | null;
  svg_download_path: string | null;
  dxf_url: string | null;
  dxf_url_expires_at: string | null;
  svg_url: string | null;
  svg_url_expires_at: string | null;
  width_mm: number;
  height_mm: number;
  utilization_pct: number;
  placements_count: number;
}

interface ViewerPlacement {
  instance_id: string;
  part_id: string;
  sheet_index: number;
  x: number;
  y: number;
  rotation_deg: number;
  width_mm: number;
  height_mm: number;
}

interface ViewerData {
  run_id: string;
  status: RunStatus;
  sheet_count: number;
  sheets: ViewerSheet[];
  placements: ViewerPlacement[];
  unplaced: Array<{ instance_id: string; part_id: string; reason: string | null }>;
}

interface MockState {
  projects: MockProject[];
  filesByProject: Record<string, MockFile[]>;
  runsByProject: Record<string, MockRun[]>;
  artifactsByRun: Record<string, MockArtifact[]>;
  viewerDataByRun: Record<string, ViewerData>;
  uploadFileTypeById: Record<string, string>;
  configCounter: number;
  runCounter: number;
  finalizedBodies: Array<Record<string, unknown>>;
}

const OWNER_ID = "e2e-user";
const NOW = "2026-02-19T00:00:00Z";
const BUNDLE_BASE64 =
  "UEsDBAoAAAAAALOgU1zpxE+FCAAAAAgAAAANABwAc2hlZXRfMDAxLmR4ZlVUCQADAl+XaQJfl2l1eAsAAQToAwAABH8AAABkeGYtZGF0YVBLAwQUAAAACACzoFNcBh9ABwoAAAALAAAADQAcAHNoZWV0XzAwMS5zdmdVVAkAAwJfl2kCX5dpdXgLAAEE6AMAAAR/AAAAsykuS7ez0QeRAFBLAQIeAwoAAAAAALOgU1zpxE+FCAAAAAgAAAANABgAAAAAAAEAAAC0gQAAAABzaGVldF8wMDEuZHhmVVQFAAMCX5dpdXgLAAEE6AMAAAR/AAAAUEsBAh4DFAAAAAgAs6BTXAYfQAcKAAAACwAAAA0AGAAAAAAAAQAAALSBTwAAAHNoZWV0XzAwMS5zdmdVVAUAAwJfl2l1eAsAAQToAwAABH8AAABQSwUGAAAAAAIAAgCmAAAAoAAAAAAA";

function json(route: Route, payload: unknown, status = 200): Promise<void> {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

function parsePath(rawPath: string): string {
  if (rawPath.startsWith("/v1")) {
    return rawPath.slice(3) || "/";
  }
  return rawPath;
}

function makeProject(id: string, name: string, description = ""): MockProject {
  return {
    id,
    owner_id: OWNER_ID,
    name,
    description,
    created_at: NOW,
    updated_at: NOW,
    archived_at: null,
  };
}

function makeRun(id: string, projectId: string, status: RunStatus, patch?: Partial<MockRun>): MockRun {
  const base: MockRun = {
    id,
    project_id: projectId,
    run_config_id: "cfg-1",
    triggered_by: OWNER_ID,
    status,
    queued_at: NOW,
    started_at: status === "queued" ? null : NOW,
    finished_at: status === "done" || status === "failed" || status === "cancelled" ? NOW : null,
    duration_sec: status === "done" ? 14.2 : null,
    solver_exit_code: status === "failed" ? 1 : null,
    error_message: status === "failed" ? "Solver failed on invalid geometry." : null,
    metrics: status === "done" ? { placements_count: 12, unplaced_count: 0, sheet_count: 1 } : null,
  };
  return { ...base, ...patch };
}

export interface MockApiOptions {
  initialProjects?: MockProject[];
  initialFilesByProject?: Record<string, MockFile[]>;
  initialRunsByProject?: Record<string, MockRun[]>;
  initialArtifactsByRun?: Record<string, MockArtifact[]>;
  initialViewerDataByRun?: Record<string, ViewerData>;
  createdRunStatus?: RunStatus;
}

export interface MockApiHandle {
  state: MockState;
  getBundleBytes(): Buffer;
  makeProject: typeof makeProject;
  makeRun: typeof makeRun;
}

export async function installMockApi(page: Page, options?: MockApiOptions): Promise<MockApiHandle> {
  const state: MockState = {
    projects: options?.initialProjects ? [...options.initialProjects] : [],
    filesByProject: options?.initialFilesByProject ? { ...options.initialFilesByProject } : {},
    runsByProject: options?.initialRunsByProject ? { ...options.initialRunsByProject } : {},
    artifactsByRun: options?.initialArtifactsByRun ? { ...options.initialArtifactsByRun } : {},
    viewerDataByRun: options?.initialViewerDataByRun ? { ...options.initialViewerDataByRun } : {},
    uploadFileTypeById: {},
    configCounter: 1,
    runCounter: 1,
    finalizedBodies: [],
  };

  const createdRunStatus = options?.createdRunStatus ?? "running";

  await page.route("**/*", async (route) => {
    const request = route.request();
    const method = request.method().toUpperCase();
    const url = new URL(request.url());
    const path = parsePath(url.pathname);

    if (url.pathname.startsWith("/signed-upload/")) {
      if (method === "PUT" || method === "POST") {
        await route.fulfill({ status: 200, body: "" });
        return;
      }
    }

    if (url.pathname === "/artifacts/mock-bundle.zip" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/zip",
        body: Buffer.from(BUNDLE_BASE64, "base64"),
      });
      return;
    }

    if (url.pathname === "/artifacts/sheet_001.svg" && method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "image/svg+xml",
        body: "<svg xmlns='http://www.w3.org/2000/svg' width='600' height='300'><rect width='600' height='300' fill='#f8fafc'/></svg>",
      });
      return;
    }

    if (!url.pathname.startsWith("/v1/")) {
      await route.continue();
      return;
    }

    if (path === "/projects" && method === "GET") {
      await json(route, { items: state.projects, total: state.projects.length, page: 1, page_size: 100 });
      return;
    }
    if (path === "/projects" && method === "POST") {
      const body = request.postDataJSON() as { name?: string; description?: string };
      const id = `project-${state.projects.length + 1}`;
      const project = makeProject(id, body.name ?? "project", body.description ?? "");
      state.projects.push(project);
      state.filesByProject[id] = state.filesByProject[id] ?? [];
      state.runsByProject[id] = state.runsByProject[id] ?? [];
      await json(route, project);
      return;
    }

    const projectMatch = path.match(/^\/projects\/([^/]+)$/);
    if (projectMatch && method === "GET") {
      const projectId = projectMatch[1];
      const project = state.projects.find((item) => item.id === projectId);
      if (!project) {
        await json(route, { message: "project not found" }, 404);
        return;
      }
      await json(route, project);
      return;
    }

    const runsListMatch = path.match(/^\/projects\/([^/]+)\/runs$/);
    if (runsListMatch && method === "GET") {
      const projectId = runsListMatch[1];
      const items = state.runsByProject[projectId] ?? [];
      await json(route, { items, total: items.length, page: 1, page_size: 100 });
      return;
    }
    if (runsListMatch && method === "POST") {
      const projectId = runsListMatch[1];
      const body = request.postDataJSON() as { run_config_id?: string };
      const runId = `run-${state.runCounter++}`;
      const run = makeRun(runId, projectId, createdRunStatus, { run_config_id: body.run_config_id ?? "cfg-1" });
      state.runsByProject[projectId] = [...(state.runsByProject[projectId] ?? []), run];
      await json(route, run);
      return;
    }

    const runMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)$/);
    if (runMatch && method === "GET") {
      const projectId = runMatch[1];
      const runId = runMatch[2];
      const run = (state.runsByProject[projectId] ?? []).find((item) => item.id === runId);
      if (!run) {
        await json(route, { message: "run not found" }, 404);
        return;
      }
      await json(route, run);
      return;
    }
    if (runMatch && method === "DELETE") {
      const projectId = runMatch[1];
      const runId = runMatch[2];
      const runs = state.runsByProject[projectId] ?? [];
      const idx = runs.findIndex((item) => item.id === runId);
      if (idx >= 0) {
        runs[idx] = makeRun(runId, projectId, "cancelled", {
          run_config_id: runs[idx].run_config_id,
          error_message: "cancel requested by user",
        });
      }
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    const runConfigMatch = path.match(/^\/projects\/([^/]+)\/run-configs$/);
    if (runConfigMatch && method === "POST") {
      const cfgId = `cfg-${state.configCounter++}`;
      await json(route, { id: cfgId });
      return;
    }

    const filesListMatch = path.match(/^\/projects\/([^/]+)\/files$/);
    if (filesListMatch && method === "GET") {
      const projectId = filesListMatch[1];
      const files = state.filesByProject[projectId] ?? [];
      await json(route, { items: files, total: files.length });
      return;
    }
    if (filesListMatch && method === "POST") {
      const projectId = filesListMatch[1];
      const body = request.postDataJSON() as {
        file_id: string;
        original_filename: string;
        storage_key?: string;
        storage_path?: string;
        file_type: string;
        size_bytes: number;
        rules_profile_snapshot_jsonb?: Record<string, unknown> | null;
      };
      state.finalizedBodies.push(request.postDataJSON() as Record<string, unknown>);
      const status = body.original_filename.toLowerCase().includes("invalid") ? "error" : "ok";
      const storageKey = body.storage_key ?? body.storage_path ?? "";
      const file: MockFile = {
        id: body.file_id,
        project_id: projectId,
        uploaded_by: OWNER_ID,
        file_type: body.file_type || state.uploadFileTypeById[body.file_id] || "part_dxf",
        original_filename: body.original_filename,
        storage_key: storageKey,
        validation_status: status,
        validation_error: status === "error" ? "Invalid DXF geometry." : null,
        uploaded_at: NOW,
      };
      state.filesByProject[projectId] = [...(state.filesByProject[projectId] ?? []), file];
      await json(route, file);
      return;
    }

    const uploadUrlMatch = path.match(/^\/projects\/([^/]+)\/files\/upload-url$/);
    if (uploadUrlMatch && method === "POST") {
      const projectId = uploadUrlMatch[1];
      const body = request.postDataJSON() as { file_type?: string; file_kind?: string };
      const fileId = `file-${(state.filesByProject[projectId] ?? []).length + 1}-${Date.now()}`;
      state.uploadFileTypeById[fileId] = body.file_type ?? body.file_kind ?? "part_dxf";
      await json(route, {
        upload_url: `http://127.0.0.1:8000/signed-upload/${fileId}`,
        file_id: fileId,
        storage_key: `users/${OWNER_ID}/projects/${projectId}/files/${fileId}/mock.dxf`,
        expires_at: "2026-12-31T23:59:59Z",
      });
      return;
    }

    const runLogMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)\/log$/);
    if (runLogMatch && method === "GET") {
      const projectId = runLogMatch[1];
      const runId = runLogMatch[2];
      const run = (state.runsByProject[projectId] ?? []).find((item) => item.id === runId);
      const runStatus = run?.status ?? "queued";
      await json(route, {
        lines: [{ line_no: 0, text: "worker: mock log line" }],
        total_lines: 1,
        next_offset: 1,
        run_status: runStatus,
        stop_polling: runStatus === "done" || runStatus === "failed" || runStatus === "cancelled",
      });
      return;
    }

    const runArtifactsMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)\/artifacts$/);
    if (runArtifactsMatch && method === "GET") {
      const runId = runArtifactsMatch[2];
      const items = state.artifactsByRun[runId] ?? [];
      await json(route, { items, total: items.length });
      return;
    }

    const artifactUrlMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)\/artifacts\/([^/]+)\/url$/);
    if (artifactUrlMatch && method === "GET") {
      const artifactId = artifactUrlMatch[3];
      await json(route, {
        artifact_id: artifactId,
        filename: `${artifactId}.dat`,
        download_url: `http://127.0.0.1:8000/artifacts/${artifactId}.dat`,
        expires_at: "2026-12-31T23:59:59Z",
      });
      return;
    }

    const bundleMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)\/artifacts\/bundle$/);
    if (bundleMatch && method === "POST") {
      await json(route, {
        artifact_id: "bundle-1",
        filename: "run_bundle.zip",
        bundle_url: "http://127.0.0.1:8000/artifacts/mock-bundle.zip",
        expires_at: "2026-12-31T23:59:59Z",
      });
      return;
    }

    const viewerMatch = path.match(/^\/projects\/([^/]+)\/runs\/([^/]+)\/viewer-data$/);
    if (viewerMatch && method === "GET") {
      const runId = viewerMatch[2];
      const viewerData = state.viewerDataByRun[runId];
      if (!viewerData) {
        await json(route, { message: "viewer data not found" }, 404);
        return;
      }
      await json(route, viewerData);
      return;
    }

    await json(route, { message: `unhandled route ${method} ${path}` }, 404);
  });

  return {
    state,
    getBundleBytes() {
      return Buffer.from(BUNDLE_BASE64, "base64");
    },
    makeProject,
    makeRun,
  };
}
