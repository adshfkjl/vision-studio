import test from "node:test";
import assert from "node:assert/strict";

import { apiUrl, imageUrl, normalizeApiBase } from "./api.js";

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
