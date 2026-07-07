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

test("polygon mode saves the class selected from the visible label dropdown", async ({ page }) => {
  let savedAnnotation = null;

  await page.route(/\/api\/tasks$/, async (route) => {
    await route.fulfill({
      json: [
        { task_type: "segment", display_name: "Segmentation", station_annotation: true, default_model: "yolov8n-seg.pt" },
      ],
    });
  });
  await page.route(/\/api\/projects$/, async (route) => {
    await route.fulfill({
      json: [
        {
          id: "segment-project",
          name: "Segment Project",
          task_type: "segment",
          schema: { task_type: "segment" },
          images: [{ name: "plot.jpg", width: 100, height: 100, annotated: false }],
        },
      ],
    });
  });
  await page.route(/\/api\/projects\/segment-project\/images(?:\?.*)?$/, async (route) => {
    await route.fulfill({ json: { total: 1, items: [{ name: "plot.jpg", width: 100, height: 100, annotated: false }] } });
  });
  await page.route(/\/api\/projects\/segment-project\/schema$/, async (route) => {
    await route.fulfill({
      json: {
        task_type: "segment",
        classes: [
          { id: 0, name: "stem", color: "#0f766e" },
          { id: 1, name: "leaf", color: "#2563eb" },
        ],
        keypoints: [],
        skeleton: [],
        flip_idx: [],
      },
    });
  });
  await page.route(/\/api\/projects\/segment-project\/validation$/, async (route) => {
    await route.fulfill({ json: { status: "ok", summary: {}, issues: [] } });
  });
  await page.route(/\/api\/projects\/segment-project\/images\/plot\.jpg$/, async (route) => {
    await route.fulfill({ contentType: "image/png", body: pixelPng });
  });
  await page.route(/\/api\/projects\/segment-project\/annotations\/plot\.jpg$/, async (route) => {
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
        annotation: { version: 1, instances: [] },
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Segment Project/ }).click();
  await page.locator(".workspace-tabs button").nth(3).click();
  await page.getByLabel("标签", { exact: true }).selectOption("1");

  const svg = page.locator(".canvas-svg");
  await expect(svg).toBeVisible();
  const box = await svg.boundingBox();
  await page.mouse.click(box.x + box.width * 0.25, box.y + box.height * 0.25);
  await page.mouse.click(box.x + box.width * 0.65, box.y + box.height * 0.25);
  await page.mouse.click(box.x + box.width * 0.45, box.y + box.height * 0.7);
  await page.keyboard.press("Space");
  await page.keyboard.press("Control+S");

  await expect.poll(() => savedAnnotation).not.toBeNull();
  expect(savedAnnotation.instances[0].type).toBe("polygon");
  expect(savedAnnotation.instances[0].class_id).toBe(1);

  await page.getByLabel("实例 #1 标签").selectOption("0");
  await page.keyboard.press("Control+S");

  await expect.poll(() => savedAnnotation.instances[0].class_id).toBe(0);
});

test("instance panel can hide instances, hide classes, and delete a whole instance", async ({ page }) => {
  let savedAnnotation = null;

  await page.route(/\/api\/tasks$/, async (route) => {
    await route.fulfill({
      json: [
        { task_type: "segment", display_name: "Segmentation", station_annotation: true, default_model: "yolov8n-seg.pt" },
      ],
    });
  });
  await page.route(/\/api\/projects$/, async (route) => {
    await route.fulfill({
      json: [
        {
          id: "visibility-project",
          name: "Visibility Project",
          task_type: "segment",
          schema: { task_type: "segment" },
          images: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }],
        },
      ],
    });
  });
  await page.route(/\/api\/projects\/visibility-project\/images(?:\?.*)?$/, async (route) => {
    await route.fulfill({ json: { total: 1, items: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }] } });
  });
  await page.route(/\/api\/projects\/visibility-project\/schema$/, async (route) => {
    await route.fulfill({
      json: {
        task_type: "segment",
        classes: [
          { id: 0, name: "stem", color: "#0f766e" },
          { id: 1, name: "leaf", color: "#2563eb" },
        ],
        keypoints: [],
        skeleton: [],
        flip_idx: [],
      },
    });
  });
  await page.route(/\/api\/projects\/visibility-project\/validation$/, async (route) => {
    await route.fulfill({ json: { status: "ok", summary: {}, issues: [] } });
  });
  await page.route(/\/api\/projects\/visibility-project\/images\/plot\.jpg$/, async (route) => {
    await route.fulfill({ contentType: "image/png", body: pixelPng });
  });
  await page.route(/\/api\/projects\/visibility-project\/annotations\/plot\.jpg$/, async (route) => {
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
              type: "polygon",
              class_id: 0,
              points: [{ x: 0.15, y: 0.15 }, { x: 0.35, y: 0.15 }, { x: 0.25, y: 0.35 }],
            },
            {
              type: "polygon",
              class_id: 1,
              points: [{ x: 0.55, y: 0.55 }, { x: 0.8, y: 0.55 }, { x: 0.68, y: 0.8 }],
            },
          ],
        },
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Visibility Project/ }).click();
  await page.locator(".workspace-tabs button").nth(3).click();
  await expect(page.getByTestId("annotation-instance-0")).toBeVisible();
  await expect(page.getByTestId("annotation-instance-1")).toBeVisible();

  await page.getByRole("button", { name: "隐藏实例 #1" }).click();
  await expect(page.getByTestId("annotation-instance-0")).toBeHidden();
  await expect(page.getByTestId("annotation-instance-1")).toBeVisible();

  await page.getByRole("button", { name: "显示实例 #1" }).click();
  await page.getByRole("button", { name: "隐藏标签 leaf" }).click();
  await expect(page.getByTestId("annotation-instance-0")).toBeVisible();
  await expect(page.getByTestId("annotation-instance-1")).toBeHidden();

  await page.getByRole("button", { name: "显示标签 leaf" }).click();
  await expect(page.getByTestId("annotation-instance-1")).toBeVisible();

  await page.getByRole("button", { name: /#2 多边形 · leaf/ }).click();
  await page.getByRole("button", { name: "删除实例 #2" }).click();
  await expect(page.getByTestId("annotation-instance-1")).toBeHidden();
  await page.keyboard.press("Control+S");

  await expect.poll(() => savedAnnotation).not.toBeNull();
  expect(savedAnnotation.instances).toHaveLength(1);
  expect(savedAnnotation.instances[0].class_id).toBe(0);
});

test("instance panel scrolls to later instances instead of clipping after the first few", async ({ page }) => {
  const instances = Array.from({ length: 12 }, (_, idx) => ({
    type: "polygon",
    class_id: idx % 2,
    points: [
      { x: 0.08, y: 0.08 },
      { x: 0.12, y: 0.08 },
      { x: 0.1, y: 0.12 },
    ],
  }));

  await page.route(/\/api\/tasks$/, async (route) => {
    await route.fulfill({
      json: [
        { task_type: "segment", display_name: "Segmentation", station_annotation: true, default_model: "yolov8n-seg.pt" },
      ],
    });
  });
  await page.route(/\/api\/projects$/, async (route) => {
    await route.fulfill({
      json: [
        {
          id: "many-instances-project",
          name: "Many Instances Project",
          task_type: "segment",
          schema: { task_type: "segment" },
          images: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }],
        },
      ],
    });
  });
  await page.route(/\/api\/projects\/many-instances-project\/images(?:\?.*)?$/, async (route) => {
    await route.fulfill({ json: { total: 1, items: [{ name: "plot.jpg", width: 100, height: 100, annotated: true }] } });
  });
  await page.route(/\/api\/projects\/many-instances-project\/schema$/, async (route) => {
    await route.fulfill({
      json: {
        task_type: "segment",
        classes: [
          { id: 0, name: "stem", color: "#0f766e" },
          { id: 1, name: "leaf", color: "#2563eb" },
        ],
        keypoints: [],
        skeleton: [],
        flip_idx: [],
      },
    });
  });
  await page.route(/\/api\/projects\/many-instances-project\/validation$/, async (route) => {
    await route.fulfill({ json: { status: "ok", summary: {}, issues: [] } });
  });
  await page.route(/\/api\/projects\/many-instances-project\/images\/plot\.jpg$/, async (route) => {
    await route.fulfill({ contentType: "image/png", body: pixelPng });
  });
  await page.route(/\/api\/projects\/many-instances-project\/annotations\/plot\.jpg$/, async (route) => {
    await route.fulfill({
      json: {
        image: "plot.jpg",
        width: 100,
        height: 100,
        annotation: { version: 1, instances },
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Many Instances Project/ }).click();
  await page.locator(".workspace-tabs button").nth(3).click();

  const instanceList = page.locator(".instances");
  await expect.poll(() => instanceList.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
  await instanceList.evaluate((el) => {
    el.scrollTop = el.scrollHeight;
  });
  await expect(page.getByRole("button", { name: /#12 多边形/ })).toBeVisible();
});
