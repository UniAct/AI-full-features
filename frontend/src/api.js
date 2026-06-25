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

async function streamReq(method, path, body, onToken) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || data.detail || data.signal || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const dataObj = JSON.parse(line.substring(6));
          if (dataObj.token) {
            fullText += dataObj.token;
            if (onToken) onToken(dataObj.token);
          }
        } catch (e) {
          // ignore malformed JSON or empty chunks
        }
      }
    }
  }
  
  return { 
    answer: fullText, 
    summary: fullText, 
    message: fullText,
    full_prompt: res.headers.get("X-Full-Prompt") ? JSON.parse(res.headers.get("X-Full-Prompt")) : null 
  };
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
  streamAnswer: (projectId, body, onToken) => streamReq('POST', `/nlp/index/answer/stream/${projectId}`, body, onToken),
  exam:       (projectId, body)    => req('POST', `/nlp/index/exam/${projectId}`, body),
  summarize:  (projectId, body)    => req('POST', `/nlp/index/summarize/${projectId}`, body),
  mindmap:    (projectId, body)    => req('POST', `/nlp/index/mindmap/${projectId}`, body),
  streamSummarize: (projectId, body, onToken) => streamReq('POST', `/nlp/index/summarize/stream/${projectId}`, body, onToken),

  // ─── Session Routes ───────────────────────────────────────────────────────
  // FIX: backend prefix is /sessions, create uses /project/{projectId} to disambiguate
  createSession: (projectId, body) => req('POST', `/sessions/project/${projectId}`, body || {}),
  listSessions:  (projectId)       => req('GET',  `/sessions/project/${projectId}/list`),
  getSession:    (projectId, sid)  => req('GET',  `/sessions/project/${projectId}/${sid}`),
  getSessionHistory: (sessionId)   => req('GET',  `/sessions/${sessionId}/history`),
  // FIX: chat route is POST /sessions/{sessionId}/chat — only sessionId in path
  chat:          (sessionId, body) => req('POST', `/sessions/${sessionId}/chat`, body),
  streamChat:    (sessionId, body, onToken) => streamReq('POST', `/sessions/${sessionId}/chat/stream`, body, onToken),

  // ─── Study Area Routes ──────────────────────────────────────────────────
  uploadStudyFile: (projectId, file) => {
    const fd = new FormData();
    fd.append('file', file);
    return req('POST', `/study/upload/${projectId}`, fd, true);
  },
  listStudyFiles:  (projectId) => req('GET', `/study/files/${projectId}`),
  getStudyData:    (projectId, fileId) => req('GET', `/study/data/${projectId}/${fileId}`),
  saveStudyData:   (projectId, fileId, body) => req('POST', `/study/data/${projectId}/${fileId}`, body),
};
