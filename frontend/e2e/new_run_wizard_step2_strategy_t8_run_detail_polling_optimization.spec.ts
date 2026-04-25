import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const PROJECT_ID = "project-t8";
const RUN_ID_DONE = "run-t8-done";
const RUN_ID_RUNNING = "run-t8-running";
const NOW = "2026-01-01T00:00:00Z";

test("T8 done-once: viewer-data fetched at most once, not repeated after polling cycles", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T8 Polling Test Project",
        description: "",
        created_at: NOW,
        updated_at: NOW,
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID_DONE,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t8",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: NOW,
          started_at: NOW,
          finished_at: NOW,
          duration_sec: 10,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 4, unplaced_count: 0, sheet_count: 1 },
        },
      ],
    },
    initialArtifactsByRun: {
      [RUN_ID_DONE]: [
        {
          id: "artifact-t8-meta",
          run_id: RUN_ID_DONE,
          artifact_type: "engine_meta",
          filename: "engine_meta.json",
          storage_key: "mock/engine_meta.json",
          size_bytes: 256,
          sheet_index: null,
          created_at: NOW,
        },
      ],
    },
    initialViewerDataByRun: {
      [RUN_ID_DONE]: {
        run_id: RUN_ID_DONE,
        status: "done",
        sheet_count: 1,
        sheets: [],
        placements: [],
        unplaced: [],
        requested_engine_backend: "auto",
        effective_engine_backend: "nesting_engine_v2",
        backend_resolution_source: "snapshot_solver_config",
        snapshot_engine_backend_hint: "nesting_engine_v2",
        strategy_profile_version_id: "version-t8-1",
        strategy_resolution_source: "run_config",
        strategy_overrides_applied: [],
        strategy_field_sources: {
          quality_profile: "run_config",
        },
      },
    },
  });

  let viewerDataRequestCount = 0;
  page.on("request", (req) => {
    if (req.method() === "GET" && req.url().includes("/viewer-data")) {
      viewerDataRequestCount++;
    }
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID_DONE}`);

  // Audit card renders with engine data
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();
  await expect(page.getByText("nesting_engine_v2").first()).toBeVisible();
  await expect(page.getByText("version-t8-1")).toBeVisible();
  await expect(page.getByText("engine_meta.json artifact present", { exact: false })).not.toBeVisible();
  await expect(page.getByText("Present")).toBeVisible();

  // Wait longer than one polling cycle (3 s) to verify the timer does not re-trigger viewer-data
  await page.waitForTimeout(4500);

  expect(viewerDataRequestCount).toBeGreaterThanOrEqual(1);
  expect(viewerDataRequestCount).toBeLessThanOrEqual(1);
});

test("T8 running-no-viewer-data: no viewer-data request while run is in running state", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T8 Running Project",
        description: "",
        created_at: NOW,
        updated_at: NOW,
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID_RUNNING,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t8r",
          triggered_by: "e2e-user",
          status: "running",
          queued_at: NOW,
          started_at: NOW,
          finished_at: null,
          duration_sec: null,
          solver_exit_code: null,
          error_message: null,
          metrics: null,
        },
      ],
    },
  });

  let viewerDataRequestCount = 0;
  page.on("request", (req) => {
    if (req.method() === "GET" && req.url().includes("/viewer-data")) {
      viewerDataRequestCount++;
    }
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID_RUNNING}`);

  // RUNNING status badge is visible (exact: true avoids case-insensitive substring match on "running" in other UI text)
  await expect(page.getByText("RUNNING", { exact: true })).toBeVisible();

  // Audit card shows "not available" fallback (not an error, expected behaviour)
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();
  await expect(page.getByText("Not available yet", { exact: false })).toBeVisible();

  // Wait longer than one polling cycle
  await page.waitForTimeout(4500);

  // No viewer-data fetch must have occurred
  expect(viewerDataRequestCount).toBe(0);

  // No global error banner set (viewer-data absence must not cause fatal error)
  // The error banner is a <p> with bg-red-50; the cancel button also uses text-danger but not bg-red-50
  await expect(page.locator("p.bg-red-50")).not.toBeVisible();
});
