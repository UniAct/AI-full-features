import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { useApp } from '../AppContext';
import { Upload, FileText, CheckCircle, Loader, Trash2 } from 'lucide-react';

function bytesToSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}

const STEPS = [
  { key: 'upload', label: 'Uploading' },
  { key: 'process', label: 'Processing' },
  { key: 'index', label: 'Indexing' },
];

export default function DocumentsPage() {
  const { projectId, triggerStamp, refreshChapters } = useApp();
  const [queue, setQueue] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1); // -1=idle, 0=upload, 1=process, 2=index
  const [currentFileIdx, setCurrentFileIdx] = useState(0);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [assets, setAssets] = useState([]);
  const [msg, setMsg] = useState(null);
  const inputRef = useRef();

  useEffect(() => {
    loadAssets();
  }, [projectId]);

  const addFiles = (fs) => {
    const newFiles = Array.from(fs);
    setQueue((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (idx) => setQueue((prev) => prev.filter((_, i) => i !== idx));

  const loadAssets = async () => {
    try {
      const res = await api.listFiles(projectId);
      setAssets(res.assets || []);
    } catch (e) {
      /* silently fail */
    }
  };

  const ingest = async () => {
    if (!queue.length) return;
    setIngesting(true);
    setMsg(null);
    setCompletedSteps([]);

    let totalChunks = 0;
    let totalVectors = 0;

    for (let i = 0; i < queue.length; i++) {
      setCurrentFileIdx(i);

      // Show upload step
      setCurrentStep(0);
      setCompletedSteps([]);

      try {
        // Simulate step progression — the backend does all 3 steps,
        // but we show progress to the user
        const stepTimer1 = setTimeout(() => {
          setCurrentStep(1);
          setCompletedSteps(['upload']);
        }, 1500);

        const stepTimer2 = setTimeout(() => {
          setCurrentStep(2);
          setCompletedSteps(['upload', 'process']);
        }, 4000);

        const res = await api.ingestFile(projectId, queue[i]);

        clearTimeout(stepTimer1);
        clearTimeout(stepTimer2);

        totalChunks += res.inserted_chunks || 0;
        totalVectors += res.indexed_vectors || 0;

        // Mark all steps done
        setCompletedSteps(['upload', 'process', 'index']);
        setCurrentStep(3);
      } catch (e) {
        setMsg({ type: 'error', text: `Failed on "${queue[i].name}": ${e.message}` });
        setIngesting(false);
        setCurrentStep(-1);
        return;
      }
    }

    setQueue([]);
    setIngesting(false);
    setCurrentStep(-1);

    triggerStamp('Ingested');
    refreshChapters();
    loadAssets();

    setMsg({
      type: 'success',
      text: `${queue.length} file(s) ingested · ${totalChunks} chunks · ${totalVectors} vectors`,
    });
  };

  return (
    <div>
      <div className="page-header">
        <h2>Documents</h2>
        <p>Upload files — they are automatically processed and indexed.</p>
      </div>
      <div className="page-body">
        {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

        <div className="card">
          <div className="card-title">Upload & Index</div>

          {/* Drop zone */}
          <div
            className={`upload-zone${dragging ? ' drag-over' : ''}`}
            onClick={() => !ingesting && inputRef.current.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              if (!ingesting) addFiles(e.dataTransfer.files);
            }}
          >
            <div className="uz-icon"><Upload size={28} /></div>
            <strong>Drop files here or click to browse</strong>
            <p>PDF and TXT supported</p>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept=".pdf,.txt"
              style={{ display: 'none' }}
              onChange={(e) => addFiles(e.target.files)}
            />
          </div>

          {/* Queued files */}
          {queue.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {queue.map((f, i) => (
                <div className="file-row" key={i}>
                  <FileText size={14} style={{ opacity: 0.5, flexShrink: 0 }} />
                  <span className="file-name">{f.name}</span>
                  <span className="file-meta">{bytesToSize(f.size)}</span>
                  {!ingesting && (
                    <button
                      className="btn btn-ghost"
                      style={{ padding: '2px 6px', fontSize: 11 }}
                      onClick={() => removeFile(i)}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Progress Stepper */}
          {ingesting && (
            <div style={{ margin: '20px 0 8px' }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                File {currentFileIdx + 1} of {queue.length}: <strong>{queue[currentFileIdx]?.name}</strong>
              </div>
              <div className="progress-stepper">
                {STEPS.map((step, i) => {
                  const isDone = completedSteps.includes(step.key);
                  const isActive = currentStep === i && !isDone;
                  return (
                    <div key={step.key} style={{ display: 'flex', alignItems: 'center' }}>
                      <div className={`step${isDone ? ' done' : isActive ? ' active' : ' pending'}`}>
                        {isDone ? (
                          <CheckCircle size={18} />
                        ) : isActive ? (
                          <Loader size={18} className="spin-icon" />
                        ) : (
                          <span className="step-num">{i + 1}</span>
                        )}
                        <span className="step-label">{step.label}</span>
                      </div>
                      {i < STEPS.length - 1 && (
                        <div className={`step-connector${isDone ? ' done' : ''}`} />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Action button */}
          <div className="btn-row">
            <button
              className="btn btn-primary"
              onClick={ingest}
              disabled={ingesting || !queue.length}
            >
              {ingesting ? (
                <><span className="spinner" />&nbsp;Ingesting…</>
              ) : (
                <>
                  <Upload size={14} style={{ marginRight: 6 }} />
                  Upload & Index {queue.length > 0 ? `(${queue.length})` : ''}
                </>
              )}
            </button>
          </div>
        </div>

        {/* Document list */}
        <div className="section-label" style={{ marginTop: 28 }}>
          Indexed Documents
          <button className="btn btn-ghost" onClick={loadAssets} style={{ marginLeft: 12, fontSize: 11, padding: '3px 10px' }}>
            ↻ Refresh
          </button>
        </div>

        {assets.length === 0 ? (
          <div className="empty-state">
            <div className="es-icon">📭</div>
            <p>No documents yet — upload a file above.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {assets.map((a) => (
              <div className="doc-card" key={a.asset_id}>
                <FileText size={18} style={{ opacity: 0.5, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="file-name" style={{ fontSize: 13 }}>
                    {a.asset_name?.replace(/^[a-z0-9]+_/, '') || a.asset_name}
                  </div>
                  <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                    <span className="file-meta">{bytesToSize(a.asset_size || 0)}</span>
                    <span className="file-meta mono-val">ID: {String(a.asset_id).slice(0, 8)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
