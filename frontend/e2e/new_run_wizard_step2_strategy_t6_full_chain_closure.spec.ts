import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";
import type { MockStrategyProfile, MockStrategyProfileVersion } from "./support/mockApi";

const NOW = "2026-01-01T00:00:00Z";
const PROJECT_ID = "project-t6";
const PROFILE_ID = "profile-t6-1";
const VERSION_ID = "version-t6-1";

const mockProfile: MockStrategyProfile = {
  id: PROFILE_ID,
  owner_user_id: "e2e-user",
  strategy_code: "t6_closure_strategy",
  display_name: "T6 Closure Strategy",
  description: "Full-chain closure strategy for T6",
  lifecycle: "active",
  is_active: true,
  metadata_jsonb: null,
  created_at: NOW,
  updated_at: NOW,
};

const mockVersion: MockStrategyProfileVersion = {
  id: VERSION_ID,
  run_strategy_profile_id: PROFILE_ID,
  owner_user_id: "e2e-user",
  version_no: 1,
  lifecycle: "active",
  is_active: true,
  solver_config_jsonb: null,
  placement_config_jsonb: null,
  manufacturing_bias_jsonb: null,
  notes: "T6 closure version",
  metadata_jsonb: null,
  created_at: NOW,
  updated_at: NOW,
};

// The first run created by mock will be "run-1" (runCounter starts at 1).
const EXPECTED_RUN_ID = "run-1";

test("T6 full-chain: Step2 custom strategy → run-config body → run create body → Run Detail audit", async ({ page }) => {
  const mock = await installMockApi(page, {
    initialStrategyProfiles: [mockProfile],
    initialStrategyVersionsByProfile: { [PROFILE_ID]: [mockVersion] },
    createdRunStatus: "done",
    initialArtifactsByRun: {
      [EXPECTED_RUN_ID]: [
        {
          id: "artifact-t6-engine-meta",
          run_id: EXPECTED_RUN_ID,
          artifact_type: "engine_meta",
          filename: "engine_meta.json",
          storage_key: "mock/engine_meta.json",
          size_bytes: 512,
          sheet_index: null,
          created_at: NOW,
        },
      ],
    },
    initialViewerDataByRun: {
      [EXPECTED_RUN_ID]: {
        run_id: EXPECTED_RUN_ID,
        status: "done",
        sheet_count: 1,
        sheets: [],
        placements: [],
        unplaced: [],
        requested_engine_backend: "auto",
        effective_engine_backend: "nesting_engine_v2",
        backend_resolution_source: "snapshot_solver_config",
        snapshot_engine_backend_hint: "nesting_engine_v2",
        strategy_profile_version_id: VERSION_ID,
        strategy_resolution_source: "run_config",
        strategy_overrides_applied: ["quality_profile", "engine_backend_hint"],
      },
    },
  });

  // Seed mock state with project and DXF source file.
  mock.state.projects.push(mock.makeProject(PROJECT_ID, "T6 Closure Project"));
  mock.state.filesByProject[PROJECT_ID] = [
    {
      id: "file-stock-t6",
      project_id: PROJECT_ID,
      uploaded_by: "e2e-user",
      file_type: "source_dxf",
      original_filename: "stock_t6.dxf",
      storage_key: "stock-t6-key",
      validation_status: "ok",
      validation_error: null,
      uploaded_at: NOW,
      latest_part_creation_projection: {
        existing_part_revision_id: "part-rev-stock-t6",
        part_creation_ready: true,
        has_nesting_derivative: true,
        readiness_reason: "ready",
        suggested_code: "stock_t6.dxf",
        suggested_name: "stock_t6.dxf",
        source_label: "stock_t6.dxf",
      },
    },
    {
      id: "file-part-t6",
      project_id: PROJECT_ID,
      uploaded_by: "e2e-user",
      file_type: "source_dxf",
      original_filename: "part_t6.dxf",
      storage_key: "part-t6-key",
      validation_status: "ok",
      validation_error: null,
      uploaded_at: NOW,
      latest_part_creation_projection: {
        existing_part_revision_id: "part-rev-part-t6",
        part_creation_ready: true,
        has_nesting_derivative: true,
        readiness_reason: "ready",
        suggested_code: "part_t6.dxf",
        suggested_name: "part_t6.dxf",
        source_label: "part_t6.dxf",
      },
    },
  ];
  mock.state.runsByProject[PROJECT_ID] = [];

  // === Wizard flow ===
  await page.goto(`/projects/${PROJECT_ID}`);
  await page.getByRole("button", { name: "New run wizard" }).click();
  await expect(page.getByRole("heading", { name: "New run wizard" })).toBeVisible();

  // Step 1: select at least one file.
  await page.locator('input[type="checkbox"]').first().check();
  await page.getByRole("button", { name: "Continue to parameters" }).click();

  // Step 2: verify strategy section is visible.
  await expect(page.getByText("Nesting strategy")).toBeVisible();

  // Choose "Custom overrides" mode.
  await page.getByRole("radio", { name: "Custom overrides" }).check();

  // Select profile and version.
  await page.getByRole("combobox", { name: "Strategy profile" }).selectOption({ value: PROFILE_ID });
  await expect(page.getByRole("combobox", { name: "Strategy version" })).not.toBeDisabled({ timeout: 5000 });
  await page.getByRole("combobox", { name: "Strategy version" }).selectOption({ value: VERSION_ID });

  // Set quality profile.
  await page.getByRole("combobox", { name: "Quality profile" }).selectOption({ value: "quality_aggressive" });

  // Set engine backend.
  await page.getByRole("combobox", { name: "Engine backend" }).selectOption({ value: "nesting_engine_v2" });

  // Set SA eval budget.
  await page.getByRole("spinbutton", { name: "SA eval budget (s)" }).fill("2");

  // Go to summary.
  await page.getByRole("button", { name: "Continue to summary" }).click();
  await expect(page.getByText(/Custom/)).toBeVisible();

  // Start run.
  await page.getByRole("button", { name: "Start run" }).click();

  // Run Detail page loads.
  await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();

  // === Assert run-config POST body ===
  const configBody = mock.state.runConfigBodies.at(-1);
  expect(configBody).toBeDefined();
  expect(configBody).toHaveProperty("run_strategy_profile_version_id", VERSION_ID);
  expect(configBody).toHaveProperty("solver_config_overrides_jsonb");
  const overrides = configBody?.solver_config_overrides_jsonb as Record<string, unknown>;
  expect(overrides.quality_profile).toBe("quality_aggressive");
  expect(overrides.engine_backend_hint).toBe("nesting_engine_v2");
  expect(typeof overrides.sa_eval_budget_sec).toBe("number");
  expect(overrides.nesting_engine_runtime_policy).toBeDefined();

  // === Assert run create POST body ===
  const runBody = mock.state.runCreateBodies.at(-1);
  expect(runBody).toBeDefined();
  expect(runBody).toHaveProperty("run_config_id");
  expect(String(runBody?.run_config_id ?? "").length).toBeGreaterThan(0);
  expect(runBody).toHaveProperty("run_strategy_profile_version_id", VERSION_ID);
  expect(runBody).toHaveProperty("quality_profile", "quality_aggressive");
  expect(runBody).toHaveProperty("engine_backend_hint", "nesting_engine_v2");
  expect(typeof runBody?.sa_eval_budget_sec).toBe("number");
  expect(runBody?.nesting_engine_runtime_policy).toBeDefined();

  // === Assert Run Detail strategy/engine audit card ===
  await expect(page.getByText("Strategy and engine audit")).toBeVisible();
  await expect(page.getByText("nesting_engine_v2").first()).toBeVisible();
  await expect(page.getByText("snapshot_solver_config")).toBeVisible();
  await expect(page.getByText(VERSION_ID)).toBeVisible();
  await expect(page.getByText("run_config")).toBeVisible();
  await expect(page.getByText("quality_profile")).toBeVisible();
  await expect(page.getByText(/Present|engine_meta\.json/i).first()).toBeVisible();
});
