import { expect, test } from "@playwright/test";

test("project center loads without a real backend database", async ({ page }) => {
  // Protects the old startup flow: the app can render the project center through mocked API responses.
  await page.route("**/api/projects", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route("**/api/tasks", async (route) => {
    await route.fulfill({
      json: [
        { task_type: "detect", display_name: "Detection", station_annotation: true, default_model: "yolov8n.pt" },
        { task_type: "segment", display_name: "Segmentation", station_annotation: true, default_model: "yolov8n-seg.pt" },
        { task_type: "pose", display_name: "Pose", station_annotation: true, default_model: "yolov8n-pose.pt" },
      ],
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Vision Studio" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "先选项目，再选训练任务" })).toBeVisible();
  await expect(page.getByRole("button", { name: /创建并进入/ })).toBeVisible();
});
