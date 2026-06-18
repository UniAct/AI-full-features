import { useState } from 'react';
import { api } from '../api';
import { useApp } from '../AppContext';

export default function SummaryPage() {
  const { projectId, triggerStamp, chapters } = useApp();
  const [selectedChapter, setSelectedChapter] = useState('all');
  const [text, setText]     = useState('');
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg]         = useState(null);

  const summarize = async () => {
    if (!text.trim() && selectedChapter === 'all') return;
    setLoading(true); setMsg(null); setSummary(null);
    try {
      const payload = { content: text };
      if (selectedChapter !== 'all') {
        try {
          const chObj = JSON.parse(selectedChapter);
          payload.chapters = [chObj.original_title];
          payload.file_chapter_filters = [{ chapter_title: chObj.original_title }];
        } catch (e) {
          payload.chapters = [selectedChapter];
          payload.file_chapter_filters = [{ chapter_title: selectedChapter }];
        }
      }
      const res = await api.summarize(projectId, payload);
      setSummary(res.summary || res.answer || JSON.stringify(res));
      triggerStamp('Summarized');
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Summarize</h2>
        <p>Paste long text and get a concise summary from the LLM.</p>
      </div>
      <div className="page-body">
        {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

        <div className="card">
          <div className="card-title">Summarize Context</div>
          {chapters && chapters.length > 0 && (
            <div className="field">
              <label>Target Chapter</label>
              <select value={selectedChapter} onChange={e => setSelectedChapter(e.target.value)}>
                <option value="all">All Chapters</option>
                {chapters.map((ch, idx) => (
                  <option key={idx} value={JSON.stringify(ch)}>{ch.chapter_title}</option>
                ))}
              </select>
            </div>
          )}
          <div className="field">
            <label>Specific Instructions or Text (Optional if Chapter selected)</label>
            <textarea rows={6} value={text} onChange={e => setText(e.target.value)}
              placeholder="e.g. Summarize the key findings..." />
          </div>
          <div className="btn-row">
            <button className="btn btn-primary" onClick={summarize} disabled={loading || (!text.trim() && selectedChapter === 'all')}>
              {loading ? <><span className="spinner"/>&nbsp;Summarizing…</> : '📄 Summarize'}
            </button>
            <button className="btn btn-ghost" onClick={() => { setText(''); setSummary(null); }}>
              Clear
            </button>
          </div>
        </div>

        {summary && (
          <>
            <div className="section-label">Summary</div>
            <div className="card" style={{ borderLeft: '3px solid var(--archive)' }}>
              <div className="result-box" style={{ border: 'none', padding: 0, background: 'transparent' }}>
                {summary}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
