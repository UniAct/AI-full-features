import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';
import { useApp } from '../AppContext';
import {
  FileText, BookOpen, StickyNote, Bookmark, BookmarkPlus,
  Trash2, Play, Pause, RotateCcw, Send, Loader,
  Clock, Zap, X, Upload
} from 'lucide-react';

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// ─── Pomodoro Timer ────────────────────────────────────────────────────────
function PomodoroTimer() {
  const WORK = 25 * 60;
  const BREAK = 5 * 60;
  const [seconds, setSeconds] = useState(WORK);
  const [running, setRunning] = useState(false);
  const [isBreak, setIsBreak] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setSeconds(s => {
          if (s <= 1) {
            clearInterval(intervalRef.current);
            setRunning(false);
            const next = !isBreak;
            setIsBreak(next);
            setSeconds(next ? BREAK : WORK);
            if (Notification.permission === 'granted') {
              new Notification(next ? '☕ Break Time! 5 minutes.' : '📚 Back to Study!');
            }
            return next ? BREAK : WORK;
          }
          return s - 1;
        });
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running, isBreak]);

  const reset = () => {
    clearInterval(intervalRef.current);
    setRunning(false);
    setIsBreak(false);
    setSeconds(WORK);
  };

  const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
  const secs = String(seconds % 60).padStart(2, '0');
  const total = isBreak ? BREAK : WORK;
  const pct = ((total - seconds) / total) * 100;
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="sa-timer">
      <div className="sa-timer-label">{isBreak ? '☕ Break' : '📚 Focus'}</div>
      <div className="sa-timer-ring">
        <svg width="72" height="72" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r={r} fill="none" stroke="var(--sa-ring-bg)" strokeWidth="5"/>
          <circle
            cx="36" cy="36" r={r} fill="none"
            stroke={isBreak ? '#22c55e' : '#6366f1'}
            strokeWidth="5"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 36 36)"
            style={{ transition: 'stroke-dasharray 1s linear' }}
          />
        </svg>
        <span className="sa-timer-time">{mins}:{secs}</span>
      </div>
      <div className="sa-timer-btns">
        <button className="sa-timer-btn" onClick={() => setRunning(r => !r)} title={running ? 'Pause' : 'Start'}>
          {running ? <Pause size={14}/> : <Play size={14}/>}
        </button>
        <button className="sa-timer-btn" onClick={reset} title="Reset"><RotateCcw size={14}/></button>
      </div>
    </div>
  );
}

// ─── Quick AI Ask ──────────────────────────────────────────────────────────
function QuickAsk({ projectId }) {
  const [query, setQuery]   = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen]     = useState(false);

  const ask = async () => {
    if (!query.trim()) return;
    setLoading(true); setAnswer(null); setOpen(true);
    try {
      const res = await api.answer(projectId, { text: query });
      setAnswer(res.answer || res.signal || 'No answer returned.');
    } catch (e) {
      setAnswer('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sa-quickask">
      <div className="sa-quickask-title"><Zap size={14}/> Quick AI Ask</div>
      <div className="sa-quickask-row">
        <input
          className="sa-quickask-input"
          placeholder="Ask anything about your documents…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && ask()}
        />
        <button className="sa-quickask-btn" onClick={ask} disabled={loading}>
          {loading ? <Loader size={14} className="spin"/> : <Send size={14}/>}
        </button>
      </div>
      {open && (
        <div className="sa-quickask-answer">
          <button className="sa-quickask-close" onClick={() => setOpen(false)}><X size={12}/></button>
          {loading ? <span className="sa-qa-loading">Thinking…</span> : <p>{answer}</p>}
        </div>
      )}
    </div>
  );
}

// ─── Main Study Area Page ──────────────────────────────────────────────────
export default function StudyAreaPage() {
  const { projectId } = useApp();
  const [files, setFiles]         = useState([]);
  const [loading, setLoading]     = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected]   = useState(null);   // asset object
  const [pdfSrc, setPdfSrc]       = useState(null);
  
  const [notes, setNotes]         = useState('');
  const [noteSaved, setNoteSaved] = useState(false);
  const [bookmarks, setBookmarks] = useState([]);
  const [bmLabel, setBmLabel]     = useState('');
  const [bmPage, setBmPage]       = useState('');
  
  const iframeRef    = useRef(null);
  const fileInputRef = useRef(null);
  const saveTimeout  = useRef(null);

  // Load study file list
  const loadFiles = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await api.listStudyFiles(projectId);
      const list = res.files || [];
      setFiles(list);
      return list;
    } catch (e) {
      console.error(e);
      return [];
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles().then(list => {
      const lastId = localStorage.getItem(`study_last_${projectId}`);
      if (lastId) {
        const found = list.find(f => f.id === lastId);
        if (found) selectFile(found);
      }
    });
  }, [projectId]);

  // Load notes + bookmarks from server when selection changes
  useEffect(() => {
    if (!selected || !projectId) {
      setNotes('');
      setBookmarks([]);
      return;
    }
    
    api.getStudyData(projectId, selected.id)
      .then(res => {
        setNotes(res.notes || '');
        setBookmarks(res.bookmarks || []);
      })
      .catch(() => {
        setNotes('');
        setBookmarks([]);
      });
      
    localStorage.setItem(`study_last_${projectId}`, selected.id);
  }, [selected, projectId]);

  const getBackendUrl = (fileId) => `${BASE}/api/v1/study/serve/${encodeURIComponent(projectId)}/${encodeURIComponent(fileId)}`;

  const selectFile = (file) => {
    setSelected(file);
    setPdfSrc(getBackendUrl(file.id));
  };

  // Upload new study PDF
  const uploadFileToServer = async (file) => {
    if (!file || file.type !== 'application/pdf') return;
    setUploading(true);
    try {
      const res = await api.uploadStudyFile(projectId, file);
      const newList = await loadFiles();
      const uploaded = newList.find(f => f.id === res.file.id);
      if (uploaded) selectFile(uploaded);
    } catch (e) {
      alert("Failed to upload study file.");
    } finally {
      setUploading(false);
    }
  };

  const handleFileInput = (e) => {
    uploadFileToServer(e.target.files?.[0]);
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = Array.from(e.dataTransfer.files).find(f => f.type === 'application/pdf');
    if (file) uploadFileToServer(file);
  };

  // Sync data to server
  const saveToServer = (newNotes, newBookmarks) => {
    if (!selected) return;
    api.saveStudyData(projectId, selected.id, {
      notes: newNotes,
      bookmarks: newBookmarks
    })
    .then(() => {
      setNoteSaved(true);
      setTimeout(() => setNoteSaved(false), 2000);
    })
    .catch(e => console.error("Failed to save study data", e));
  };

  const handleNoteChange = useCallback((val) => {
    setNotes(val);
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(() => {
      saveToServer(val, bookmarks);
    }, 1500);
  }, [selected, projectId, bookmarks]);

  const addBookmark = () => {
    if (!bmLabel.trim() || !selected) return;
    const bm = { label: bmLabel.trim(), page: parseInt(bmPage) || 1 };
    const updated = [...bookmarks, bm];
    setBookmarks(updated);
    saveToServer(notes, updated);
    setBmLabel(''); setBmPage('');
  };

  const deleteBookmark = (idx) => {
    const updated = bookmarks.filter((_, i) => i !== idx);
    setBookmarks(updated);
    saveToServer(notes, updated);
  };

  const jumpToPage = (page) => {
    if (!iframeRef.current || !pdfSrc) return;
    iframeRef.current.src = pdfSrc.split('#')[0] + `#page=${page}`;
  };

  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="sa-root">
      <input ref={fileInputRef} type="file" accept="application/pdf" style={{ display:'none' }} onChange={handleFileInput}/>

      {/* ── Left Panel ── */}
      <div className="sa-left">
        <PomodoroTimer />

        {/* Upload button */}
        <button className="sa-open-btn" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
          {uploading ? <Loader size={15} className="spin" /> : <Upload size={15}/>} 
          {uploading ? "Uploading..." : "Upload Study PDF"}
        </button>

        {/* File selector */}
        <div className="sa-section">
          <div className="sa-section-title"><BookOpen size={14}/> Study PDFs</div>
          {loading && !uploading ? (
            <div className="sa-loading"><Loader size={14} className="spin"/> Loading…</div>
          ) : files.length === 0 ? (
            <div className="sa-empty">No PDFs uploaded yet.</div>
          ) : (
            <ul className="sa-filelist">
              {files.map(f => (
                <li
                  key={f.id}
                  className={`sa-fileitem${selected?.id === f.id ? ' active' : ''}`}
                  onClick={() => selectFile(f)}
                >
                  <FileText size={14} className="sa-fileicon"/>
                  <div className="sa-file-info">
                    <span className="sa-filename">{f.name}</span>
                    {f.size && <span className="sa-filesize">{formatSize(f.size)}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Notes */}
        <div className="sa-section sa-notes-section">
          <div className="sa-section-title">
            <StickyNote size={14}/> Study Notes
            {noteSaved && <span className="sa-saved">✓ Saved to cloud</span>}
          </div>
          <textarea
            className="sa-notes"
            placeholder={selected ? `Notes for ${selected.name}…` : 'Select a document to take notes…'}
            value={notes}
            onChange={e => handleNoteChange(e.target.value)}
            disabled={!selected}
          />
        </div>

        {/* Bookmarks */}
        <div className="sa-section">
          <div className="sa-section-title"><Bookmark size={14}/> Bookmarks</div>
          <div className="sa-bm-add">
            <input className="sa-bm-label" placeholder="Label…" value={bmLabel} onChange={e => setBmLabel(e.target.value)} disabled={!pdfSrc}/>
            <input className="sa-bm-page" placeholder="Pg" type="number" min="1" value={bmPage} onChange={e => setBmPage(e.target.value)} disabled={!pdfSrc} onKeyDown={e => e.key === 'Enter' && addBookmark()}/>
            <button className="sa-bm-btn" onClick={addBookmark} disabled={!pdfSrc || !bmLabel.trim()}><BookmarkPlus size={14}/></button>
          </div>
          {bookmarks.length === 0 ? (
            <div className="sa-empty">No bookmarks yet.</div>
          ) : (
            <ul className="sa-bmlist">
              {bookmarks.map((bm, i) => (
                <li key={i} className="sa-bmitem">
                  <button className="sa-bmjump" onClick={() => jumpToPage(bm.page)}><Clock size={11}/> p.{bm.page}</button>
                  <span className="sa-bmlabel">{bm.label}</span>
                  <button className="sa-bmdel" onClick={() => deleteBookmark(i)}><Trash2 size={11}/></button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <QuickAsk projectId={projectId} />
      </div>

      {/* ── Right Panel ── */}
      <div className="sa-right" onDragOver={e => e.preventDefault()} onDrop={handleDrop}>
        {!selected ? (
          /* No file selected yet */
          <div className="sa-placeholder">
            <div className="sa-ph-icon"><BookOpen size={56}/></div>
            <h2 className="sa-ph-title">Study Area</h2>
            <p className="sa-ph-sub">Upload a PDF to your Study Space to start reading</p>
            <button className="sa-ph-open-btn" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              {uploading ? <Loader size={16} className="spin" /> : <Upload size={16}/>} 
              {uploading ? "Uploading..." : "Upload Study PDF"}
            </button>
            <p className="sa-ph-drag">or drag & drop a PDF here</p>
            <div className="sa-ph-hints">
              <span>📝 Auto-saved notes per document</span>
              <span>🔖 Jump-to-page bookmarks</span>
              <span>⏱ Focus timer built-in</span>
              <span>⚡ Ask AI without leaving</span>
            </div>
          </div>
        ) : (
          /* Show PDF viewer */
          <>
            <div className="sa-viewer-header">
              <FileText size={15}/>
              <span className="sa-viewer-title">{selected.name}</span>
              <span className="sa-server-badge" style={{background: '#dcfce7', color: '#166534'}}>📚 Study Storage</span>
            </div>
            {pdfSrc ? (
              <iframe
                ref={iframeRef}
                key={pdfSrc}
                src={pdfSrc}
                className="sa-iframe"
                title={selected.name}
                allow="fullscreen"
              />
            ) : (
              <div className="sa-loading" style={{justifyContent:'center', padding:'40px'}}>
                <Loader size={20} className="spin"/> Loading file…
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
