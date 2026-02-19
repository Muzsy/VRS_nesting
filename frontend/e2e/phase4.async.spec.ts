import { expect, test } from "@playwright/test";
import { installMockApi } from "./support/mockApi";

test.describe("Phase 4 async E2E suite", () => {
  test("Async E2E#3: FAILED run -> error rendered on run detail", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("project-async", "Async Project"));
    mock.state.filesByProject["project-async"] = [];
    mock.state.runsByProject["project-async"] = [
      mock.makeRun("run-failed", "project-async", "failed", {
        error_message: "Solver failed due to malformed polygon.",
      }),
    ];

    await page.goto("/projects/project-async/runs/run-failed");
    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();
    await expect(page.getByText("FAILED", { exact: true })).toBeVisible();
    await expect(page.getByText("Solver failed due to malformed polygon.")).toBeVisible();
  });

  test("Async E2E#4: done run -> viewer reachable", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("project-viewer", "Viewer Project"));
    mock.state.filesByProject["project-viewer"] = [];
    mock.state.runsByProject["project-viewer"] = [mock.makeRun("run-done", "project-viewer", "done")];
    mock.state.viewerDataByRun["run-done"] = {
      run_id: "run-done",
      status: "done",
      sheet_count: 1,
      sheets: [
        {
          sheet_index: 0,
          dxf_artifact_id: "a-dxf-1",
          svg_artifact_id: "a-svg-1",
          dxf_filename: "sheet_001.dxf",
          svg_filename: "sheet_001.svg",
          dxf_download_path: "/v1/projects/project-viewer/runs/run-done/artifacts/a-dxf-1/download",
          svg_download_path: "/v1/projects/project-viewer/runs/run-done/artifacts/a-svg-1/download",
          dxf_url: "http://127.0.0.1:8000/artifacts/sheet_001.dxf",
          dxf_url_expires_at: "2026-12-31T23:59:59Z",
          svg_url: "http://127.0.0.1:8000/artifacts/sheet_001.svg",
          svg_url_expires_at: "2026-12-31T23:59:59Z",
          width_mm: 600,
          height_mm: 300,
          utilization_pct: 84.3,
          placements_count: 2,
        },
      ],
      placements: [
        {
          instance_id: "inst-1",
          part_id: "part-A",
          sheet_index: 0,
          x: 10,
          y: 20,
          rotation_deg: 0,
          width_mm: 40,
          height_mm: 20,
        },
      ],
      unplaced: [],
    };

    await page.goto("/projects/project-viewer/runs/run-done");
    await expect(page.getByRole("heading", { name: "Run detail" })).toBeVisible();
    await page.getByRole("link", { name: "Open viewer" }).click();

    await expect(page).toHaveURL(/\/viewer$/);
    await expect(page.getByRole("heading", { name: "Layout viewer" })).toBeVisible();
    await expect(page.getByText("sheet_count: 1")).toBeVisible();
    await expect(page.getByText("mode: svg")).toBeVisible();
  });

  test("Async E2E#5: ZIP bundle download contains DXF + SVG names", async ({ page }) => {
    const mock = await installMockApi(page);
    mock.state.projects.push(mock.makeProject("project-export", "Export Project"));
    mock.state.filesByProject["project-export"] = [];
    mock.state.runsByProject["project-export"] = [mock.makeRun("run-export", "project-export", "done")];
    mock.state.artifactsByRun["run-export"] = [
      {
        id: "artifact-dxf",
        run_id: "run-export",
        artifact_type: "sheet_dxf",
        filename: "sheet_001.dxf",
        storage_key: "runs/run-export/artifacts/sheet_001.dxf",
        size_bytes: 1234,
        sheet_index: 0,
        created_at: "2026-02-19T00:00:00Z",
      },
      {
        id: "artifact-svg",
        run_id: "run-export",
        artifact_type: "sheet_svg",
        filename: "sheet_001.svg",
        storage_key: "runs/run-export/artifacts/sheet_001.svg",
        size_bytes: 4321,
        sheet_index: 0,
        created_at: "2026-02-19T00:00:01Z",
      },
    ];

    await page.goto("/projects/project-export/runs/run-export/export");
    await expect(page.getByRole("heading", { name: "Export center" })).toBeVisible();

    await page.getByRole("button", { name: "Create ZIP bundle" }).click();
    const bundleLink = page.getByRole("link", { name: "run_bundle.zip" });
    await expect(bundleLink).toBeVisible();

    const href = await bundleLink.getAttribute("href");
    expect(href).toBeTruthy();

    const bytes = await page.evaluate(async (url) => {
      const response = await fetch(url);
      const data = await response.arrayBuffer();
      return Array.from(new Uint8Array(data));
    }, href as string);

    const zipped = Buffer.from(bytes);
    const zipText = zipped.toString("latin1");
    expect(zipText).toContain("sheet_001.dxf");
    expect(zipText).toContain("sheet_001.svg");
    expect(zipped.equals(mock.getBundleBytes())).toBeTruthy();
  });
});
