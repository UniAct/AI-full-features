const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const API  = `${BASE}/api/v1`;

async function req(method, path, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body !== undefined && body !== null) {
    if (isForm) {
      opts.body = body;
    } else {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
  }
  const res = await fetch(`${API}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.detail || data.signal || `HTTP ${res.status}`);
  return data;
}

export const api = {
  // Health check
  health: ()                       => req('GET',  '/'),

  // ─── Data Routes ─────────────────────────────────────────────────────────
  uploadFile: (projectId, file)    => {
    const fd = new FormData();
    fd.append('file', file);
    return req('POST', `/data/upload/${projectId}`, fd, true);
  },
  processFiles: (projectId, body)  => req('POST', `/data/process/${projectId}`, body),
  listFiles:    (projectId)        => req('GET',  `/data/files/${projectId}`),
  listChapters: (projectId)        => req('GET',  `/data/chapters/${projectId}`),
  ingestFile:   (projectId, file)  => {
    const fd = new FormData();
    fd.append('file', file);
    return req('POST', `/data/ingest/${projectId}`, fd, true);
  },

  // ─── NLP / Index Routes ───────────────────────────────────────────────────
  pushIndex:  (projectId, body)    => req('POST', `/nlp/index/push/${projectId}`, body),
  indexInfo:  (projectId)          => req('GET',  `/nlp/index/info/${projectId}`),
  search:     (projectId, body)    => req('POST', `/nlp/index/search/${projectId}`, body),
  answer:     (projectId, body)    => req('POST', `/nlp/index/answer/${projectId}`, body),
  exam:       (projectId, body)    => req('POST', `/nlp/index/exam/${projectId}`, body),
  summarize:  (projectId, body)    => req('POST', `/nlp/index/summarize/${projectId}`, body),

  // ─── Session Routes ───────────────────────────────────────────────────────
  // FIX: backend prefix is /sessions, create uses /project/{projectId} to disambiguate
  createSession: (projectId, body) => req('POST', `/sessions/project/${projectId}`, body || {}),
  listSessions:  (projectId)       => req('GET',  `/sessions/project/${projectId}/list`),
  getSession:    (projectId, sid)  => req('GET',  `/sessions/project/${projectId}/${sid}`),
  getSessionHistory: (sessionId)   => req('GET',  `/sessions/${sessionId}/history`),
  // FIX: chat route is POST /sessions/{sessionId}/chat — only sessionId in path
  chat:          (sessionId, body) => req('POST', `/sessions/${sessionId}/chat`, body),
};
