import { useState } from 'react';
import DocumentPanel from './documentpanel';

export default function ConversationSidebar({ conversations, activeId, loading, error, openingId, disabled, onOpen, onNew, onRefresh }) {
  const [view, setView] = useState('history');
  const [search, setSearch] = useState('');
  const filtered = conversations.filter((conversation) => (conversation.name || 'Untitled conversation').toLowerCase().includes(search.trim().toLowerCase()));

  return <aside className="workspace-sidebar" aria-label="Workspace navigation">
    <div className="sidebar-switch" aria-label="Sidebar view">
      <button aria-pressed={view === 'history'} onClick={() => setView('history')}>Conversations</button>
      <button aria-pressed={view === 'documents'} onClick={() => setView('documents')}>Knowledge Base</button>
    </div>
    <div className="history-panel" hidden={view !== 'history'}>
      <button className="sidebar-new" onClick={onNew}><span aria-hidden="true">＋</span> New conversation</button>
      <label className="sr-only" htmlFor="conversation-search">Search conversations</label>
      <input id="conversation-search" className="history-search" type="search" placeholder="Search conversations…" value={search} onChange={(event) => setSearch(event.target.value)} />
      <div className="history-heading"><h2>Recent conversations</h2><button className="refresh-files" onClick={onRefresh} disabled={loading}>Refresh</button></div>
      {loading && <p className="document-status" role="status">Loading conversations…</p>}
      {error && <div className="document-error" role="alert"><p>{error}</p><button onClick={onRefresh} disabled={loading}>Retry</button></div>}
      {!loading && !error && !conversations.length && <p className="history-empty">No conversations yet.<br />Ask a question to start your first chat.</p>}
      {!loading && conversations.length > 0 && !filtered.length && <p className="history-empty">No conversations match your search.</p>}
      <nav className="history-list" aria-label="Conversation history" aria-busy={loading}>
        <ul>{filtered.map((conversation) => <li key={conversation.id}>
          <button className="history-item" aria-current={activeId === conversation.id ? 'page' : undefined} disabled={disabled} onClick={() => onOpen(conversation)} title={conversation.name || 'Untitled conversation'}>
            <span className="history-title">{conversation.name || 'Untitled conversation'}</span>
            <span className="history-meta">{openingId === conversation.id ? 'Opening…' : conversation.created_at && !Number.isNaN(Date.parse(conversation.created_at)) ? <time dateTime={conversation.created_at}>{new Date(conversation.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time> : 'Saved conversation'}</span>
          </button>
        </li>)}</ul>
      </nav>
    </div>
    <div className="sidebar-documents" hidden={view !== 'documents'}><DocumentPanel /></div>
  </aside>;
}
