import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

const MOCK_DXF = Buffer.from("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n", "utf-8");

test.describe("Phase 4 stable E2E suite", () => {
  test("Stable E2E#1: auth -> project -> upload -> run start -> running -> cancel", async ({ page }) => {
    await installMockApi(page);

    await page.goto("/auth?mode=login");
    await expect(page).toHaveURL(/\/projects$/);

    await page.getByPlaceholder("Project name").fill("Stable Project");
    await page.getByRole("button", { name: "New project" }).click();
    await expect(page.getByRole("link", { name: "Stable Project" })).toBeVisible();

    await page.getByRole("link", { name: "Stable Project" }).click();
    await expect(page.getByRole("button", { name: "New run wizard" })).toBeVisible();

    await page.getByRole("button", { name: "Upload as stock DXF" }).click();
    await page.locator('input[type="file"]').setInputFiles([{ name: "stock_ok.dxf", mimeType: "application/dxf", buffer: MOCK_DXF }]);
    await expect(page.getByText("Upload complete")).toBeVisible();

    await page.getByRole("button", { name: "Upload as part DXF" }).click();
    await page.locator('input[type="file"]').setInputFiles([{ name: "part_ok.dxf", mimeType: "application/dxf", buffer: MOCK_DXF }]);
    await expect(page.getByText("part_ok.dxf")).toBeVisible();

    await page.getByRole("button", { name: "New run wizard" }).click();
    await expect(page.getByRole("heading", { name: "New run wizard" })).toBeVisible();

    await page.locator('input[type="checkbox"]').first().check();
    await page.getByRole("button", { name: "Continue to parameters" }).click();
    await page.getByRole("button", { name: "Continue to summary" }).click();
    await page.getByRole("button", { name: "Start run" }).click();

    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();
    await expect(page.getByText("RUNNING", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Cancel run" }).click();
    await expect(page.getByText("CANCELLED", { exact: true })).toBeVisible();
  });

  test("Stable E2E#2: invalid DXF upload -> validation error badge", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("project-invalid", "Invalid Upload Project"));
    mock.state.filesByProject["project-invalid"] = [];
    mock.state.runsByProject["project-invalid"] = [];

    await page.goto("/projects/project-invalid");
    await expect(page.getByRole("button", { name: "Upload as part DXF" })).toBeVisible();

    await page.getByRole("button", { name: "Upload as part DXF" }).click();
    await page.locator('input[type="file"]').setInputFiles([{ name: "part_invalid.dxf", mimeType: "application/dxf", buffer: MOCK_DXF }]);

    await expect(page.getByText("part_invalid.dxf")).toBeVisible();
    await expect(page.getByText("Invalid DXF geometry.")).toBeVisible();
    await expect(page.getByText("error")).toBeVisible();
  });
});
