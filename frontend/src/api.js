export function normalizeApiBase(value = "") {
  return String(value || "").trim().replace(/\/+$/, "");
}

const RAW_API_BASE = import.meta.env?.VITE_API_BASE || "";
const API_BASE = normalizeApiBase(RAW_API_BASE);

function apiPath(path) {
  return `${API_BASE}${path}`;
}

async function request(path, options = {}) {
  const response = await fetch(apiPath(path), {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

async function uploadRequest(path, files) {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  const response = await fetch(apiPath(path), { method: "POST", body });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

async function multipartRequest(path, fields = {}, files = {}) {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") body.append(key, value);
  });
  Object.entries(files).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (item) body.append(key, item);
      });
      return;
    }
    if (value) body.append(key, value);
  });
  const response = await fetch(apiPath(path), { method: "POST", body });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

export const apiBase = API_BASE || "same-origin";

export const api = {
  projects: () => request("/api/projects"),
  tasks: () => request("/api/tasks"),
  devices: () => request("/api/devices"),
  jobs: (projectId, kind = "") => request(`/api/jobs?project_id=${encodeURIComponent(projectId)}${kind ? `&kind=${encodeURIComponent(kind)}` : ""}`),
  createProject: (payload) => request("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  importProject: (payload) => request("/api/projects/import", { method: "POST", body: JSON.stringify(payload) }),
  importProjectFile: (payload, annotationFiles) => multipartRequest("/api/projects/import-file", payload, { annotation_files: annotationFiles }),
  importCurrent: () => request("/api/demo/import-current", { method: "POST" }),
  images: (projectId) => request(`/api/projects/${projectId}/images?limit=500`),
  uploadImages: (projectId, files) => uploadRequest(`/api/projects/${projectId}/images/upload`, files),
  deleteImage: (projectId, imageName) => request(`/api/projects/${projectId}/images/${encodeURIComponent(imageName)}`, { method: "DELETE" }),
  importAnnotations: (projectId, payload) => request(`/api/projects/${projectId}/annotations/import`, { method: "POST", body: JSON.stringify(payload) }),
  importAnnotationFile: (projectId, payload, annotationFiles) => multipartRequest(`/api/projects/${projectId}/annotations/import-file`, payload, { annotation_files: annotationFiles }),
  schema: (projectId) => request(`/api/projects/${projectId}/schema`),
  saveSchema: (projectId, schema) => request(`/api/projects/${projectId}/schema`, { method: "PUT", body: JSON.stringify(schema) }),
  validation: (projectId) => request(`/api/projects/${projectId}/validation`),
  annotation: (projectId, imageName) => request(`/api/projects/${projectId}/annotations/${encodeURIComponent(imageName)}`),
  saveAnnotation: (projectId, imageName, annotation) =>
    request(`/api/projects/${projectId}/annotations/${encodeURIComponent(imageName)}`, {
      method: "PUT",
      body: JSON.stringify(annotation),
    }),
  split: (projectId, payload) => request(`/api/projects/${projectId}/split`, { method: "POST", body: JSON.stringify(payload) }),
  materialize: (projectId) => request(`/api/projects/${projectId}/materialize`, { method: "POST" }),
  train: (projectId, payload) => request(`/api/projects/${projectId}/train`, { method: "POST", body: JSON.stringify(payload) }),
  predict: (payload) => request("/api/predict", { method: "POST", body: JSON.stringify(payload) }),
  prelabel: (projectId, payload) => request(`/api/projects/${projectId}/prelabel`, { method: "POST", body: JSON.stringify(payload) }),
  job: (jobId) => request(`/api/jobs/${jobId}`),
  pauseJob: (jobId) => request(`/api/jobs/${jobId}/pause`, { method: "POST" }),
  resumeJob: (jobId) => request(`/api/jobs/${jobId}/resume`, { method: "POST" }),
  stopJob: (jobId) => request(`/api/jobs/${jobId}/stop`, { method: "POST" }),
  exportOnnx: (jobId) => request(`/api/jobs/${jobId}/export/onnx`, { method: "POST" }),
};

export function imageUrl(projectId, imageName) {
  return apiPath(`/api/projects/${projectId}/images/${encodeURIComponent(imageName)}`);
}

export function artifactUrl(jobId, artifactName) {
  return apiPath(`/api/artifacts/${jobId}/${encodeURIComponent(artifactName)}`);
}

export function apiUrl(path) {
  return apiPath(path);
}
