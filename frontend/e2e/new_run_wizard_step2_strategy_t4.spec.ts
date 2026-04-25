import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";
import type { MockStrategyProfile, MockStrategyProfileVersion } from "./support/mockApi";

const NOW = "2026-01-01T00:00:00Z";
const PROJECT_ID = "project-strategy-t4";
const PROFILE_ID = "profile-t4-1";
const VERSION_ID = "version-t4-1";

const mockProfile: MockStrategyProfile = {
  id: PROFILE_ID,
  owner_user_id: "e2e-user",
  strategy_code: "t4_test_strategy",
  display_name: "T4 Test Strategy",
  description: "E2E test strategy profile for T4",
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
  notes: "T4 test version",
  metadata_jsonb: null,
  created_at: NOW,
  updated_at: NOW,
};

test.describe("New Run Wizard Step2 Strategy T4", () => {
  test("T4: custom strategy payload flows into run-config and run POST bodies", async ({ page }) => {
    const mock = await installMockApi(page, {
      initialStrategyProfiles: [mockProfile],
      initialStrategyVersionsByProfile: { [PROFILE_ID]: [mockVersion] },
    });

    // Pre-populate project and files so we skip the upload flow.
    mock.state.projects.push(mock.makeProject(PROJECT_ID, "Strategy T4 Project"));
    mock.state.filesByProject[PROJECT_ID] = [
      {
        id: "file-stock-1",
        project_id: PROJECT_ID,
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "stock.dxf",
        storage_key: "stock-key",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: NOW,
        latest_part_creation_projection: {
          existing_part_revision_id: "part-rev-stock-1",
          part_creation_ready: true,
          has_nesting_derivative: true,
          readiness_reason: "ready",
          suggested_code: "stock.dxf",
          suggested_name: "stock.dxf",
          source_label: "stock.dxf",
        },
      },
      {
        id: "file-part-1",
        project_id: PROJECT_ID,
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "part.dxf",
        storage_key: "part-key",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: NOW,
        latest_part_creation_projection: {
          existing_part_revision_id: "part-rev-part-1",
          part_creation_ready: true,
          has_nesting_derivative: true,
          readiness_reason: "ready",
          suggested_code: "part.dxf",
          suggested_name: "part.dxf",
          source_label: "part.dxf",
        },
      },
    ];
    mock.state.runsByProject[PROJECT_ID] = [];

    // Navigate to project page and open wizard.
    await page.goto(`/projects/${PROJECT_ID}`);
    await page.getByRole("button", { name: "New run wizard" }).click();
    await expect(page.getByRole("heading", { name: "New run wizard" })).toBeVisible();

    // Step 1: check the first checkbox (any DXF file as part) and continue.
    await page.locator('input[type="checkbox"]').first().check();
    await page.getByRole("button", { name: "Continue to parameters" }).click();

    // Step 2: strategy UI should be visible.
    await expect(page.getByText("Nesting strategy")).toBeVisible();

    // Select "Custom overrides".
    await page.getByRole("radio", { name: "Custom overrides" }).check();

    // Select the strategy profile.
    await page.getByRole("combobox", { name: "Strategy profile" }).selectOption({ value: PROFILE_ID });

    // Wait for version selector to be populated, then select the version.
    await expect(page.getByRole("combobox", { name: "Strategy version" })).not.toBeDisabled({ timeout: 5000 });
    await page.getByRole("combobox", { name: "Strategy version" }).selectOption({ value: VERSION_ID });

    // Select quality_aggressive.
    await page.getByRole("combobox", { name: "Quality profile" }).selectOption({ value: "quality_aggressive" });

    // Select nesting_engine_v2.
    await page.getByRole("combobox", { name: "Engine backend" }).selectOption({ value: "nesting_engine_v2" });

    // Set SA eval budget to 2.
    await page.getByRole("spinbutton", { name: "SA eval budget (s)" }).fill("2");

    // Proceed to Step 3 summary.
    await page.getByRole("button", { name: "Continue to summary" }).click();

    // Verify strategy appears in summary.
    await expect(page.getByText(/Custom/)).toBeVisible();

    // Start run.
    await page.getByRole("button", { name: "Start run" }).click();

    // Wait for navigation to run detail.
    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();

    // Assert run-config POST body.
    const configBody = mock.state.runConfigBodies.at(-1);
    expect(configBody).toBeDefined();
    expect(configBody).toHaveProperty("run_strategy_profile_version_id", VERSION_ID);
    expect(configBody).toHaveProperty("solver_config_overrides_jsonb");
    const overrides = configBody?.solver_config_overrides_jsonb as Record<string, unknown>;
    expect(overrides).toBeDefined();
    expect(overrides.quality_profile).toBe("quality_aggressive");
    expect(overrides.engine_backend_hint).toBe("nesting_engine_v2");
    expect(typeof overrides.sa_eval_budget_sec).toBe("number");
    expect(overrides.nesting_engine_runtime_policy).toBeDefined();

    // Assert run POST body.
    const runBody = mock.state.runCreateBodies.at(-1);
    expect(runBody).toBeDefined();
    expect(runBody).toHaveProperty("run_config_id");
    expect(String(runBody?.run_config_id ?? "").length).toBeGreaterThan(0);
    expect(runBody).toHaveProperty("run_strategy_profile_version_id", VERSION_ID);
    expect(runBody).toHaveProperty("quality_profile", "quality_aggressive");
    expect(runBody).toHaveProperty("engine_backend_hint", "nesting_engine_v2");
    expect(typeof runBody?.sa_eval_budget_sec).toBe("number");
    expect(runBody?.nesting_engine_runtime_policy).toBeDefined();
  });

  test("T4: project_default mode sends only run_config_id (no explicit strategy override)", async ({ page }) => {
    const mock = await installMockApi(page, {
      initialStrategyProfiles: [mockProfile],
      initialStrategyVersionsByProfile: { [PROFILE_ID]: [mockVersion] },
    });

    mock.state.projects.push(mock.makeProject(PROJECT_ID, "Strategy T4 Default Project"));
    mock.state.filesByProject[PROJECT_ID] = [
      {
        id: "file-s2",
        project_id: PROJECT_ID,
        uploaded_by: "e2e-user",
        file_type: "source_dxf",
        original_filename: "stock2.dxf",
        storage_key: "s2",
        validation_status: "ok",
        validation_error: null,
        uploaded_at: NOW,
        latest_part_creation_projection: {
          existing_part_revision_id: "part-rev-s2",
          part_creation_ready: true,
          has_nesting_derivative: true,
          readiness_reason: "ready",
          suggested_code: "stock2.dxf",
          suggested_name: "stock2.dxf",
          source_label: "stock2.dxf",
        },
      },
    ];
    mock.state.runsByProject[PROJECT_ID] = [];

    await page.goto(`/projects/${PROJECT_ID}`);
    await page.getByRole("button", { name: "New run wizard" }).click();
    await page.locator('input[type="checkbox"]').first().check();
    await page.getByRole("button", { name: "Continue to parameters" }).click();

    // Default strategy source is "project_default" — no changes needed.
    await page.getByRole("button", { name: "Continue to summary" }).click();
    await page.getByRole("button", { name: "Start run" }).click();
    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();

    const runBody = mock.state.runCreateBodies.at(-1);
    expect(runBody).toBeDefined();
    // run_config_id must be present (the critical bug fix).
    expect(runBody).toHaveProperty("run_config_id");
    expect(String(runBody?.run_config_id ?? "").length).toBeGreaterThan(0);
    // No explicit strategy override fields in project_default mode.
    expect(runBody?.run_strategy_profile_version_id).toBeUndefined();
    expect(runBody?.quality_profile).toBeUndefined();
    expect(runBody?.engine_backend_hint).toBeUndefined();
  });
});
