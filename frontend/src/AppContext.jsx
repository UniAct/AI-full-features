import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const Ctx = createContext(null);

export function AppProvider({ children }) {
  const [projectId, setProjectId] = useState('my-project');
  const [health, setHealth] = useState(null);   // null | true | false
  const [stamp, setStamp] = useState(null);      // null | string label
  const [chapters, setChapters] = useState([]);

  const triggerStamp = useCallback((label = 'Done') => {
    setStamp(label);
    setTimeout(() => setStamp(null), 2200);
  }, []);

  const refreshChapters = useCallback(() => {
    import('./api').then(({ api }) => {
      api.listChapters(projectId)
        .then(res => setChapters(res.chapters || []))
        .catch(() => setChapters([]));
    });
  }, [projectId]);

  useEffect(() => {
    const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
    const check = () =>
      fetch(`${BASE}/api/v1/`, { redirect: 'follow' })
        .then(r => { if (r.ok || r.status === 303) return true; throw new Error(); })
        .then(() => setHealth(true))
        .catch(() => setHealth(false));

    check();
    // Retry every 15s so it recovers after Modal cold start
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    refreshChapters();
  }, [projectId, refreshChapters]);

  return (
    <Ctx.Provider value={{ projectId, setProjectId, health, triggerStamp, chapters, refreshChapters }}>
      {children}
      {stamp && (
        <div className="stamp-overlay">
          <div className="stamp-mark">{stamp}</div>
        </div>
      )}
    </Ctx.Provider>
  );
}

export const useApp = () => useContext(Ctx);
