import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const PROJECT_ID = "project-t5";
const RUN_ID = "run-t5";

test("T5: Run Detail strategy and engine audit card shows observability fields", async ({ page }) => {
  const mock = await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T5 Audit Project",
        description: "T5 test project",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t5",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: "2026-01-01T00:00:00Z",
          started_at: "2026-01-01T00:00:01Z",
          finished_at: "2026-01-01T00:00:15Z",
          duration_sec: 14,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 5, unplaced_count: 0, sheet_count: 1 },
        },
      ],
    },
    initialArtifactsByRun: {
      [RUN_ID]: [
        {
          id: "artifact-engine-meta",
          run_id: RUN_ID,
          artifact_type: "engine_meta",
          filename: "engine_meta.json",
          storage_key: "mock/engine_meta.json",
          size_bytes: 512,
          sheet_index: null,
          created_at: "2026-01-01T00:00:15Z",
        },
      ],
    },
    initialViewerDataByRun: {
      [RUN_ID]: {
        run_id: RUN_ID,
        status: "done",
        sheet_count: 1,
        sheets: [],
        placements: [],
        unplaced: [],
        requested_engine_backend: "auto",
        effective_engine_backend: "nesting_engine_v2",
        backend_resolution_source: "snapshot_solver_config",
        snapshot_engine_backend_hint: "nesting_engine_v2",
        strategy_profile_version_id: "version-t5-1",
        strategy_resolution_source: "run_config",
        strategy_overrides_applied: ["quality_profile", "engine_backend_hint"],
      },
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);

  await expect(page.getByText("Strategy and engine audit")).toBeVisible();
  await expect(page.getByText("nesting_engine_v2").first()).toBeVisible();
  await expect(page.getByText("snapshot_solver_config")).toBeVisible();
  await expect(page.getByText("version-t5-1")).toBeVisible();
  await expect(page.getByText("run_config")).toBeVisible();
  await expect(page.getByText("quality_profile")).toBeVisible();
  await expect(page.getByText(/engine_meta\.json.*artifact|artifact.*engine_meta\.json|Present/i).first()).toBeVisible();

  // ensure main run card is intact
  await expect(page.getByText("DONE")).toBeVisible();

  // suppress unused-variable lint
  void mock;
});

test("T5 regression: Run Detail page loads without viewer-data, shows fallback audit text", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T5 Regression Project",
        description: "",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t5b",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: "2026-01-01T00:00:00Z",
          started_at: "2026-01-01T00:00:01Z",
          finished_at: "2026-01-01T00:00:10Z",
          duration_sec: 9,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 3, unplaced_count: 0, sheet_count: 1 },
        },
      ],
    },
    // No viewerDataByRun — 404 will be returned
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);

  // Run Detail page still loads
  await expect(page.getByText("Run detail")).toBeVisible();
  await expect(page.getByText("DONE")).toBeVisible();

  // Strategy audit card present with fallback text
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();
  await expect(page.getByText(/Not available yet/i)).toBeVisible();

  // No global fatal error banner caused by missing viewer-data
  const errorBanner = page.locator("p.text-danger");
  const errorCount = await errorBanner.count();
  if (errorCount > 0) {
    const text = await errorBanner.first().textContent();
    // only acceptable error is unrelated to viewer-data
    expect(text).not.toContain("viewer");
    expect(text).not.toContain("viewer-data");
  }
});
