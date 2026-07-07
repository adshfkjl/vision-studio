import { expect, test } from "@playwright/test";

const pixelPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
  "base64",
);

test("mouse mode drags a pose keypoint before the containing bbox interior", async ({ page }) => {
  let savedAnnotation = null;

  await page.route(/\/api\/tasks$/, async (route) => {
    await route.fulfill({
      json: [
        { task_type: "pose", display_name: "Pose", station_annotation: true, default_model: "yolov8n-pose.pt" },
      ],
    });
  });
  await page.route(/\/api\/projects$/, async (route) => {
    await route.fulfill({
      json: [
        {
          id: "pose-project",
          name: "Pose Project",
          task_type: "pose",
          schema: { task_type: "pose" },
          images: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }],
        },
      ],
    });
  });
  await page.route(/\/api\/projects\/pose-project\/images(?:\?.*)?$/, async (route) => {
    await route.fulfill({ json: { total: 1, items: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }] } });
  });
  await page.route(/\/api\/projects\/pose-project\/schema$/, async (route) => {
    await route.fulfill({
      json: {
        task_type: "pose",
        classes: [{ id: 0, name: "stem", color: "#0f766e" }],
        keypoints: ["tip"],
        skeleton: [],
        flip_idx: [0],
      },
    });
  });
  await page.route(/\/api\/projects\/pose-project\/validation$/, async (route) => {
    await route.fulfill({ json: { status: "ok", summary: {}, issues: [] } });
  });
  await page.route(/\/api\/projects\/pose-project\/images\/plot\.jpg$/, async (route) => {
    await route.fulfill({ contentType: "image/png", body: pixelPng });
  });
  await page.route(/\/api\/projects\/pose-project\/annotations\/plot\.jpg$/, async (route) => {
    if (route.request().method() === "PUT") {
      savedAnnotation = route.request().postDataJSON();
      await route.fulfill({ json: { ok: true } });
      return;
    }
    await route.fulfill({
      json: {
        image: "plot.jpg",
        width: 100,
        height: 100,
        annotation: {
          version: 1,
          instances: [
            {
              type: "pose",
              class_id: 0,
              bbox: { cx: 0.5, cy: 0.5, w: 0.6, h: 0.6 },
              keypoints: [{ name: "tip", x: 0.5, y: 0.5, v: 2 }],
            },
          ],
        },
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Pose Project/ }).click();
  await page.locator(".workspace-tabs button").nth(3).click();
  await page.keyboard.press("v");

  const svg = page.locator(".canvas-svg");
  await expect(svg).toBeVisible();

  const instanceRow = page.getByRole("button", { name: /#1 姿态 · stem 框 \+ 1\/1 关键点/ });
  await expect(instanceRow).toBeVisible();
  await instanceRow.click();
  await expect(page.getByTestId("selected-bbox-0")).toBeVisible();
  await expect(page.getByTestId("selected-keypoint-0-tip")).toBeVisible();

  const box = await svg.boundingBox();
  const startX = box.x + box.width * 0.5;
  const startY = box.y + box.height * 0.5;
  const endX = box.x + box.width * 0.62;
  const endY = box.y + box.height * 0.58;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY);
  await page.mouse.up();
  await page.keyboard.press("Control+S");

  await expect.poll(() => savedAnnotation).not.toBeNull();
  const instance = savedAnnotation.instances[0];
  expect(instance.bbox).toEqual({ cx: 0.5, cy: 0.5, w: 0.6, h: 0.6 });
  expect(instance.keypoints[0].x).toBeGreaterThan(0.58);
  expect(instance.keypoints[0].y).toBeGreaterThan(0.54);
});
