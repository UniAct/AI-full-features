import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { useApp } from '../AppContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatPage() {
  const { projectId, chapters } = useApp();
  const [sessionId, setSessionId] = useState(null);
  const [sessionsList, setSessionsList] = useState([]);
  const [history, setHistory]     = useState([]);
  const [input, setInput]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [creating, setCreating]   = useState(false);
  const [msg, setMsg]             = useState(null);
  const feedRef = useRef();

  const [selectedChapter, setSelectedChapter] = useState('all');

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [history, loading]);

  useEffect(() => {
    fetchSessions();
  }, [projectId]);

  const fetchSessions = async () => {
    try {
      const res = await api.listSessions(projectId);
      setSessionsList(res.sessions || []);
    } catch (e) {
      console.error("Failed to load sessions", e);
    }
  };

  const loadSession = async (sid) => {
    setLoading(true); setMsg(null);
    try {
      setSessionId(sid);
      const res = await api.getSessionHistory(sid);
      const reversed = (res.history || []).reverse();
      setHistory(reversed);
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };

  const createSession = async () => {
    setCreating(true); setMsg(null);
    try {
      const payload = {};
      if (selectedChapter !== 'all') {
        payload.filters = [{ chapter_title: selectedChapter }];
        payload.title = `Chat: ${selectedChapter}`;
      } else {
        payload.title = "New Chat";
      }
      const res = await api.createSession(projectId, payload);
      setSessionId(res.session_id);
      setHistory([]);
      fetchSessions();
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    } finally {
      setCreating(false);
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || !sessionId) return;
    setInput('');
    setHistory(h => [...h, { role: 'user', content: text }, { role: 'assistant', content: '' }]);
    setLoading(true);
    try {
      await api.streamChat(sessionId, { text }, (token) => {
        setHistory(h => {
          const newH = [...h];
          newH[newH.length - 1].content += token;
          return newH;
        });
      });
    } catch (e) {
      setHistory(h => {
        const newH = [...h];
        newH[newH.length - 1].content = `Error: ${e.message}`;
        return newH;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Session Chat</h2>
        <p>Multi-turn conversation with full context history.</p>
      </div>
      <div className="page-body">
        {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

        <div style={{ display: 'flex', gap: 20 }}>
          {/* Sidebar */}
          <div className="card" style={{ width: 250, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
            <div className="card-title" style={{ marginBottom: 12 }}>Past Sessions</div>
            <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {sessionsList.map(s => (
                <div 
                  key={s.session_id} 
                  onClick={() => loadSession(s.session_id)}
                  style={{
                    padding: '8px 12px', 
                    cursor: 'pointer', 
                    borderRadius: 4, 
                    backgroundColor: sessionId === s.session_id ? 'var(--bg2)' : 'transparent',
                    border: '1px solid var(--border)'
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 'bold' }}>{s.title || 'Untitled'}</div>
                  <div style={{ fontSize: 11, color: 'var(--pencil)' }}>{s.created_at ? new Date(s.created_at).toLocaleString() : ''}</div>
                </div>
              ))}
              {sessionsList.length === 0 && <div style={{ fontSize: 12, color: 'var(--pencil)', textAlign: 'center', marginTop: 20 }}>No past sessions.</div>}
            </div>
          </div>

          {/* Main Chat Area */}
          <div style={{ flex: 1 }}>
            {!sessionId ? (
              <div className="card" style={{ textAlign: 'center', padding: '40px 24px', height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>🗣️</div>
                <p style={{ color: 'var(--pencil)', marginBottom: 20 }}>Start a new session to begin chatting.</p>
                <div className="field" style={{ width: '100%', maxWidth: 400, textAlign: 'left', marginBottom: 20 }}>
                  <label>Restrict Chat to Chapter</label>
                  <select value={selectedChapter} onChange={e => setSelectedChapter(e.target.value)}>
                    <option value="all">All Indexed Content</option>
                    {chapters.map(ch => (
                      <option key={ch.chapter_title} value={ch.chapter_title}>
                        [{ch.file_name}] {ch.chapter_title}
                      </option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-primary" onClick={createSession} disabled={creating}>
                  {creating ? <><span className="spinner"/>&nbsp;Creating…</> : '+ New Session'}
                </button>
              </div>
            ) : (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <span className="mono-val" style={{ fontSize: 10 }}>Session: {sessionId.slice(0, 16)}…</span>
                  <button className="btn btn-ghost" style={{ fontSize: 11, padding: '3px 10px' }} onClick={() => setSessionId(null)}>
                    + New Session
                  </button>
                </div>

                <div ref={feedRef} className="chat-feed" style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>
                  {history.length === 0 && (
                    <div className="empty-state">
                      <div className="es-icon">💬</div>
                      <p>Type a message to start.</p>
                    </div>
                  )}
                  {history.map((m, i) => (
                    <div key={i} className={`chat-bubble ${m.role} ${m.role === 'assistant' ? 'markdown-body' : ''}`}>
                      {m.role === 'assistant' ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                      ) : (
                        m.content
                      )}
                      {loading && i === history.length - 1 && <span className="blinking-cursor">▌</span>}
                    </div>
                  ))}
                </div>

                <div className="chat-input-row" style={{ marginTop: 16 }}>
                  <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
                    placeholder="Type a message… (Enter to send)"
                    rows={2}
                  />
                  <button className="btn btn-primary" onClick={send} disabled={loading || !input.trim()}>
                    Send
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
