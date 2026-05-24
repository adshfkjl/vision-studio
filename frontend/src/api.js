const RAW_API_BASE = import.meta.env.VITE_API_BASE?.trim() || "";
const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

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

export const apiBase = API_BASE || "same-origin";

export const api = {
  projects: () => request("/api/projects"),
  tasks: () => request("/api/tasks"),
  createProject: (payload) => request("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  importProject: (payload) => request("/api/projects/import", { method: "POST", body: JSON.stringify(payload) }),
  importCurrent: () => request("/api/demo/import-current", { method: "POST" }),
  images: (projectId) => request(`/api/projects/${projectId}/images?limit=500`),
  uploadImages: (projectId, files) => uploadRequest(`/api/projects/${projectId}/images/upload`, files),
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
  job: (jobId) => request(`/api/jobs/${jobId}`),
  exportOnnx: (jobId) => request(`/api/jobs/${jobId}/export/onnx`, { method: "POST" }),
};

export function imageUrl(projectId, imageName) {
  return apiPath(`/api/projects/${projectId}/images/${encodeURIComponent(imageName)}`);
}

export function artifactUrl(jobId, artifactName) {
  return apiPath(`/api/artifacts/${jobId}/${encodeURIComponent(artifactName)}`);
}
