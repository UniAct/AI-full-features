import { useState } from 'react';
import { AppProvider, useApp } from './AppContext';
import Rail from './Rail';
import DocumentsPage from './pages/DocumentsPage';
import SearchPage    from './pages/SearchPage';
import AnswerPage    from './pages/AnswerPage';
import ChatPage      from './pages/ChatPage';
import ExamPage      from './pages/ExamPage';
import SummaryPage   from './pages/SummaryPage';
import MindMapPage   from './pages/MindMapPage';
import StudyAreaPage from './pages/StudyAreaPage';

const PAGES = {
  docs:    DocumentsPage,
  search:  SearchPage,
  answer:  AnswerPage,
  chat:    ChatPage,
  exam:    ExamPage,
  summary: SummaryPage,
  mindmap: MindMapPage,
  study:   StudyAreaPage,
};

function Shell() {
  const { health, projectId, setProjectId } = useApp();
  const [active, setActive] = useState('docs');
  const Page = PAGES[active] || DocumentsPage;

  return (
    <div className="app-shell">
      <Rail active={active} onSelect={setActive} />
      <div className="main-area">
        {health === false && (
          <div className="health-bar offline">
            ⚠ API is offline — Modal cloud backend is starting up, please wait a moment and refresh
          </div>
        )}
        {health === true && (
          <div className="health-bar" title="API connected"></div>
        )}
        
        {/* Top Header */}
        <header className="top-bar">
          <div className="tb-left">
            <h1 className="tb-title">UniAct Assistant</h1>
          </div>
          <div className="tb-right">
            <label className="tb-label">Project ID:</label>
            <input 
              className="tb-input"
              value={projectId}
              onChange={e => setProjectId(e.target.value)}
              placeholder="my-project"
              spellCheck={false}
            />
            <div className="user-avatar">AK</div>
          </div>
        </header>

        <div className="page-content">
          <Page />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
