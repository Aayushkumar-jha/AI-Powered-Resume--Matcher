import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 120000,
});

api.interceptors.request.use((config) => {
  const key = import.meta.env.VITE_API_KEY;
  if (key) config.headers["X-API-Key"] = key;
  return config;
});

/** Turn any axios error into a readable message. */
export function errorMessage(err) {
  if (!err) return "Unknown error";
  if (err.response) {
    const d = err.response.data;
    if (d?.errors?.length) return d.errors.map((e) => `${e.field || "input"}: ${e.message}`).join("; ");
    if (typeof d?.detail === "string") return d.detail;
    return `Request failed (${err.response.status})`;
  }
  if (err.request) return "Cannot reach the backend API. Is the FastAPI server running on port 8000?";
  return err.message;
}

export const JobsAPI = {
  list: () => api.get("/jobs").then((r) => r.data),
  get: (id) => api.get(`/jobs/${id}`).then((r) => r.data),
  create: (raw_text, title) => api.post("/jobs", { raw_text, title: title || null }).then((r) => r.data),
  upload: (file, title) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    return api.post("/jobs/upload", fd).then((r) => r.data);
  },
  update: (id, payload) => api.put(`/jobs/${id}`, payload).then((r) => r.data),
  remove: (id) => api.delete(`/jobs/${id}`),
};

export const ResumesAPI = {
  list: (jobId) => api.get(`/jobs/${jobId}/resumes`).then((r) => r.data),
  upload: (jobId, files, onProgress) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return api
      .post(`/jobs/${jobId}/resumes`, fd, {
        onUploadProgress: (e) => onProgress?.(e.total ? Math.round((e.loaded / e.total) * 100) : 0),
      })
      .then((r) => r.data);
  },
  remove: (jobId, resumeId) => api.delete(`/jobs/${jobId}/resumes/${resumeId}`),
  download: (jobId, resumeId) =>
    api.get(`/jobs/${jobId}/resumes/${resumeId}/file`, { responseType: "blob" }).then((r) => r.data),
};

export const AnalysisAPI = {
  start: (jobId) => api.post(`/jobs/${jobId}/analyze`).then((r) => r.data),
  status: (jobId) => api.get(`/jobs/${jobId}/status`).then((r) => r.data),
  candidates: (jobId, params) => api.get(`/jobs/${jobId}/candidates`, { params }).then((r) => r.data),
  candidate: (jobId, cid) => api.get(`/jobs/${jobId}/candidates/${cid}`).then((r) => r.data),
  compare: (jobId, ids) => api.get(`/jobs/${jobId}/compare`, { params: { ids: ids.join(",") } }).then((r) => r.data),
  dashboard: (jobId) => api.get(`/jobs/${jobId}/dashboard`).then((r) => r.data),
  exportCsv: (jobId) => api.get(`/jobs/${jobId}/export`, { responseType: "blob" }),
};

export const SystemAPI = {
  health: () => api.get("/health").then((r) => r.data),
  defaults: () => api.get("/config/defaults").then((r) => r.data),
};

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default api;
