import { useEffect, useState } from 'react';
import { getAuditEvents } from '../services/api';

const labelize = (value) => value ? value.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase()) : '—';
const eventLabels = {
  request_started: 'Request started', response_generated: 'Response generated',
  model_called: 'Model called', tool_called: 'Tool called', document_retrieved: 'Document retrieved',
  guardrail: 'Guardrail', request_failed: 'Request failed',
};

const sourceLabels = {
  user_input: 'User message', internal_retrieval: 'Retrieved document', web_search: 'Web result',
  stored_user_facts: 'Stored user facts', delegated_analysis_context: 'Delegated context',
  tool_query: 'Tool query', save_user_fact: 'Save user fact',
};

export default function GuardrailPage({ onBack, onSignOut }) {
  const [events, setEvents] = useState([]);
  const [eventType, setEventType] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setEvents([]);
    setHasMore(false);
    getAuditEvents({ offset, eventType, status, signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) { setEvents(data.events); setHasMore(data.has_more); }
    }).catch((error) => {
      if (!controller.signal.aborted) setError(error.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [offset, eventType, status, refresh]);

  return <main className="audit-page">
    <header className="conversation-header"><div><p className="audit-eyebrow">ADMIN · LEVEL 3</p><h1>AI Governance</h1><p className="account-caption">Review AI activity, model calls, document retrieval, and guardrails across your workspace.</p></div><div className="header-actions"><button className="new-chat" onClick={onBack}>Back to chat</button><button className="new-chat" onClick={onSignOut}>Sign out</button></div></header>
    <p className="audit-explainer">Events contain activity metadata. Times use your local timezone. Guardrail flags are heuristic warnings; the requesting user may not have authored flagged content.</p>
    <div className="audit-toolbar"><div className="audit-filters">
      <label htmlFor="audit-event">Event <select id="audit-event" value={eventType} onChange={(event) => { setEventType(event.target.value); setOffset(0); }}><option value="">All activity</option>{Object.entries(eventLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label htmlFor="audit-status">Status <select id="audit-status" value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}><option value="">All statuses</option>{['started', 'success', 'failed', 'flagged', 'blocked'].map((value) => <option key={value} value={value}>{labelize(value)}</option>)}</select></label>
    </div><button className="new-chat" disabled={loading} onClick={() => { setOffset(0); setRefresh((value) => value + 1); }}>Refresh</button></div>
    {loading && <p role="status" className="audit-empty">Loading AI activity…</p>}
    {error && <div className="error-notice" role="alert">{error}<button onClick={() => setRefresh((value) => value + 1)}>Retry</button></div>}
    {!loading && !error && !events.length && <div className="audit-empty"><h2>No AI activity {eventType || status ? 'matching these filters' : 'yet'}</h2><p>New events appear here after requests finish.</p></div>}
    {!loading && !error && events.length > 0 && <div className="audit-table-scroll" tabIndex={0} role="region" aria-label="AI audit events"><table className="audit-table"><thead><tr><th scope="col">Time</th><th scope="col">Requesting user</th><th scope="col">Event</th><th scope="col">Resource</th><th scope="col">Status</th><th scope="col">Details</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}>
      <td><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></td>
      <td><strong>{event.user_name || 'Unknown user'}</strong><span>{event.user_email}</span><small>Level {event.user_access}</small><details><summary>User ID</summary><code>{event.user_id}</code></details></td>
      <td>{eventLabels[event.event_type] || labelize(event.event_type)}<small>{sourceLabels[event.source] || labelize(event.source)}</small></td>
      <td>{event.model || event.tool || event.details?.filename || event.details?.rule || event.document_id || '—'}</td>
      <td><span className={`audit-badge audit-${event.status}`}>{labelize(event.status)}</span></td>
      <td>{event.details && Object.entries(event.details).map(([key, value]) => <p key={key}><strong>{labelize(key)}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</p>)}{event.document_id && <details><summary>Document ID</summary><code>{event.document_id}</code></details>}<details><summary>Conversation ID</summary><code>{event.conversation_id}</code></details></td>
    </tr>)}</tbody></table></div>}
    <footer className="audit-pagination"><button className="new-chat" disabled={loading || offset === 0} onClick={() => setOffset((value) => Math.max(0, value - 25))}>Previous</button><span>Page {Math.floor(offset / 25) + 1}</span><button className="new-chat" disabled={loading || !hasMore || Boolean(error)} onClick={() => setOffset((value) => value + 25)}>Next</button></footer>
  </main>;
}
