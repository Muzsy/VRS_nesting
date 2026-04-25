import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const PROJECT_ID = "project-t7";
const RUN_ID = "run-t7";
const NOW = "2026-01-01T00:00:00Z";

test("T7: Strategy field sources breakdown renders sorted key/source pairs", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T7 Field Sources Project",
        description: "",
        created_at: NOW,
        updated_at: NOW,
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t7",
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
      [RUN_ID]: [
        {
          id: "artifact-t7-meta",
          run_id: RUN_ID,
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
        strategy_profile_version_id: "version-t7-1",
        strategy_resolution_source: "run_config",
        strategy_overrides_applied: ["quality_profile", "engine_backend_hint"],
        strategy_field_sources: {
          quality_profile: "run_config",
          engine_backend_hint: "request",
          nesting_engine_runtime_policy: "global_default",
        },
      },
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);

  // Existing audit card present
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();

  // Field sources section heading
  await expect(page.getByText("Strategy field sources")).toBeVisible();

  // Key/source pairs (sorted: engine_backend_hint, nesting_engine_runtime_policy, quality_profile)
  await expect(page.getByText(/quality_profile.*run_config|run_config.*quality_profile/)).toBeVisible();
  await expect(page.getByText(/engine_backend_hint.*request|request.*engine_backend_hint/)).toBeVisible();
  await expect(page.getByText(/nesting_engine_runtime_policy.*global_default|global_default.*nesting_engine_runtime_policy/)).toBeVisible();

  // Existing audit fields still present
  await expect(page.getByText("version-t7-1")).toBeVisible();
  await expect(page.getByText("nesting_engine_v2").first()).toBeVisible();
});

test("T7 fallback: empty strategy_field_sources shows stable fallback", async ({ page }) => {
  await installMockApi(page, {
    initialProjects: [
      {
        id: PROJECT_ID,
        owner_id: "e2e-user",
        name: "T7 Fallback Project",
        description: "",
        created_at: NOW,
        updated_at: NOW,
        archived_at: null,
      },
    ],
    initialRunsByProject: {
      [PROJECT_ID]: [
        {
          id: RUN_ID,
          project_id: PROJECT_ID,
          run_config_id: "cfg-t7b",
          triggered_by: "e2e-user",
          status: "done",
          queued_at: NOW,
          started_at: NOW,
          finished_at: NOW,
          duration_sec: 8,
          solver_exit_code: 0,
          error_message: null,
          metrics: { placements_count: 2, unplaced_count: 0, sheet_count: 1 },
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
        strategy_field_sources: null,
      },
    },
  });

  await page.goto(`/projects/${PROJECT_ID}/runs/${RUN_ID}`);

  // Page loads without error
  await expect(page.getByText("Run detail")).toBeVisible();

  // Audit card present
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();

  // Field sources section with fallback
  await expect(page.getByText("Strategy field sources")).toBeVisible();
  await expect(page.getByText("No field source evidence")).toBeVisible();
});
