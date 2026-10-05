import { useEffect, useState } from 'react';
import { getGuardrailEvents } from '../services/api';

const sourceLabels = {
  user_input: 'User message', internal_retrieval: 'Retrieved document', web_search: 'Web result',
  stored_user_facts: 'Stored user facts', delegated_analysis_context: 'Delegated context',
  tool_query: 'Tool query', save_user_fact: 'Save user fact',
};

export default function GuardrailPage({ onBack, onSignOut }) {
  const [events, setEvents] = useState([]);
  const [action, setAction] = useState('');
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
    getGuardrailEvents({ offset, action, signal: controller.signal }).then((data) => {
      if (!controller.signal.aborted) { setEvents(data.events); setHasMore(data.has_more); }
    }).catch((error) => {
      if (!controller.signal.aborted) setError(error.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [offset, action, refresh]);

  return <main className="audit-page">
    <header className="conversation-header"><div><p className="audit-eyebrow">ADMIN · LEVEL 3</p><h1>Guardrail activity</h1><p className="account-caption">Review guardrail hits across your workspace.</p></div><div className="header-actions"><button className="new-chat" onClick={onBack}>Back to chat</button><button className="new-chat" onClick={onSignOut}>Sign out</button></div></header>
    <p className="audit-explainer">Flags are heuristic warnings, not confirmed attacks. The user shown initiated the request; they may not have authored flagged documents, web results, or delegated content.</p>
    <div className="audit-toolbar"><label htmlFor="audit-action">Outcome <select id="audit-action" value={action} onChange={(event) => { setAction(event.target.value); setOffset(0); }}><option value="">All outcomes</option><option value="flagged">Flagged · warning only</option><option value="blocked">Blocked · invalid tool input</option></select></label><button className="new-chat" disabled={loading} onClick={() => { setOffset(0); setRefresh((value) => value + 1); }}>Refresh</button></div>
    {loading && <p role="status" className="audit-empty">Loading guardrail activity…</p>}
    {error && <div className="error-notice" role="alert">{error}<button onClick={() => setRefresh((value) => value + 1)}>Retry</button></div>}
    {!loading && !error && !events.length && <div className="audit-empty"><h2>No guardrail hits {action ? 'for this outcome' : 'yet'}</h2><p>New hits appear here after requests finish. Earlier activity was not recorded.</p></div>}
    {!loading && !error && events.length > 0 && <div className="audit-table-scroll" tabIndex={0} role="region" aria-label="Guardrail events"><table className="audit-table"><thead><tr><th scope="col">Time</th><th scope="col">Requesting user</th><th scope="col">Source</th><th scope="col">Outcome</th><th scope="col">Details</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}>
      <td><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time></td>
      <td><strong>{event.user_name || 'Unknown user'}</strong><span>{event.user_email}</span><small>Level {event.user_access}</small><details><summary>User ID</summary><code>{event.user_id}</code></details></td>
      <td>{sourceLabels[event.source] || event.source}</td>
      <td><span className={`audit-badge ${event.action === 'blocked' ? 'audit-blocked' : ''}`}>{event.action === 'blocked' ? 'Blocked' : 'Flagged'}</span></td>
      <td><strong>{event.rule === 'possible_prompt_injection' ? 'Possible prompt injection' : event.rule === 'invalid_tool_input' ? 'Invalid tool input' : event.rule}</strong><p>{event.reason}</p><details><summary>Conversation ID</summary><code>{event.conversation_id}</code></details></td>
    </tr>)}</tbody></table></div>}
    <footer className="audit-pagination"><button className="new-chat" disabled={loading || offset === 0} onClick={() => setOffset((value) => Math.max(0, value - 25))}>Previous</button><span>Page {Math.floor(offset / 25) + 1}</span><button className="new-chat" disabled={loading || !hasMore || Boolean(error)} onClick={() => setOffset((value) => value + 25)}>Next</button></footer>
  </main>;
}
