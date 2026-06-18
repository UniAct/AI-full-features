import { useApp } from './AppContext';
import { FolderOpen, Search, MessageSquare, MessagesSquare, GraduationCap, FileText, Bot } from 'lucide-react';

const DRAWERS = [
  { id: 'docs',    icon: FolderOpen,     label: 'Documents' },
  { id: 'search',  icon: Search,         label: 'Search' },
  { id: 'answer',  icon: MessageSquare,  label: 'RAG Answer' },
  { id: 'chat',    icon: MessagesSquare,  label: 'Session Chat' },
  { id: 'exam',    icon: GraduationCap,  label: 'Exam' },
  { id: 'summary', icon: FileText,       label: 'Summarize' },
];

export default function Rail({ active, onSelect }) {
  const { health } = useApp();

  return (
    <aside className="rail">
      <div className="rail-logo" title="UniAct System">
        <Bot size={28} className="logo-icon" />
      </div>

      <nav className="rail-nav">
        {DRAWERS.map(d => {
          const Icon = d.icon;
          const isActive = active === d.id;
          return (
            <button
              key={d.id}
              className={`drawer-btn${isActive ? ' active' : ''}`}
              onClick={() => onSelect(d.id)}
              title={d.label}
            >
              <Icon size={22} className="drawer-icon" />
            </button>
          );
        })}
      </nav>

      <div className="rail-footer" title={health === null ? 'Checking API...' : health ? 'API Online' : 'API Offline'}>
        <span className={`status-dot ${health ? 'green' : 'red'}`} />
      </div>
    </aside>
  );
}
