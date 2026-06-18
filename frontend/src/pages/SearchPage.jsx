import { useState } from 'react';
import { api } from '../api';
import { useApp } from '../AppContext';
import { Search as SearchIcon } from 'lucide-react';

export default function SearchPage() {
  const { projectId, chapters } = useApp();
  const [selectedChapter, setSelectedChapter] = useState('all');
  const [query, setQuery]   = useState('');
  const [limit, setLimit]   = useState(5);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg]         = useState(null);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true); setMsg(null); setResults([]);
    try {
      const payload = { text: query, limit };
      if (selectedChapter !== 'all') {
        try {
          const chObj = JSON.parse(selectedChapter);
          payload.file_chapter_filters = [{ chapter_title: chObj.original_title }];
        } catch {
          payload.file_chapter_filters = [{ chapter_title: selectedChapter }];
        }
      }
      const res = await api.search(projectId, payload);
      setResults(res.results || []);
      if (!res.results?.length) setMsg({ type: 'info', text: 'No results found.' });
    } catch (e) {
      setMsg({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Semantic Search</h2>
        <p>Search indexed documents by meaning — no exact match needed.</p>
      </div>
      <div className="page-body">
        {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

        <div className="card">
          <div className="card-title">Search Query</div>
          <div className="field">
            <label>Your query</label>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && search()}
              placeholder="What do you want to find?"
            />
          </div>
          {chapters && chapters.length > 0 && (
            <div className="field">
              <label>Target Chapter</label>
              <select value={selectedChapter} onChange={e => setSelectedChapter(e.target.value)}>
                <option value="all">All Indexed Content</option>
                {chapters.map((ch, idx) => (
                  <option key={idx} value={JSON.stringify(ch)}>{ch.chapter_title}</option>
                ))}
              </select>
            </div>
          )}
          <div className="field">
            <label>Results limit — {limit}</label>
            <input type="range" min={1} max={20} value={limit}
              onChange={e => setLimit(+e.target.value)} />
          </div>
          <div className="btn-row">
            <button className="btn btn-primary" onClick={search} disabled={loading || !query.trim()}>
              {loading ? <><span className="spinner"/>&nbsp;Searching…</> : <><SearchIcon size={14} style={{ marginRight: 6 }} /> Search</>}
            </button>
          </div>
        </div>

        {results.length > 0 && (
          <>
            <div className="section-label">{results.length} Results</div>
            {results.map((r, i) => (
              <div className="search-card" key={i}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                  <span className="mono-val" style={{ fontSize: 10 }}>#{i + 1}</span>
                  <span className="score-pill">{r.score?.toFixed(4)}</span>
                </div>
                <div className="sc-text">{r.text}</div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
