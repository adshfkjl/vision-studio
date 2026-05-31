import test from "node:test";
import assert from "node:assert/strict";

import { api, apiUrl, imageUrl, normalizeApiBase } from "./api.js";

test("normalizeApiBase trims whitespace and trailing slashes", () => {
  // Protects the old custom VITE_API_BASE behavior while avoiding double slashes in API URLs.
  assert.equal(normalizeApiBase("  http://127.0.0.1:8010///  "), "http://127.0.0.1:8010");
});

test("apiUrl keeps same-origin API paths relative by default", () => {
  // Protects the old collaborator-friendly proxy behavior: no hardcoded 127.0.0.1 API base is required.
  assert.equal(apiUrl("/api/projects"), "/api/projects");
});

test("imageUrl encodes image names without changing the project route", () => {
  // Protects image display for uploaded files whose names contain spaces or non-ASCII characters.
  assert.equal(imageUrl("project-1", "leaf sample 01.jpg"), "/api/projects/project-1/images/leaf%20sample%2001.jpg");
});

test("importAnnotationFile appends multiple files to multipart form data", async () => {
  const seen = {};
  const files = [
    new File(["0 0.1 0.2 0.3 0.4"], "one.txt", { type: "text/plain" }),
    new File(["0 0.5 0.6 0.7 0.8"], "two.txt", { type: "text/plain" }),
  ];

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    seen.body = options.body;
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    await api.importAnnotationFile("project-1", { annotation_format: "auto" }, files);
  } finally {
    globalThis.fetch = originalFetch;
  }

  const entries = Array.from(seen.body.entries());
  const fileEntries = entries.filter(([key]) => key === "annotation_files");
  assert.equal(fileEntries.length, 2);
  assert.equal(fileEntries[0][1].name, "one.txt");
  assert.equal(fileEntries[1][1].name, "two.txt");
});
