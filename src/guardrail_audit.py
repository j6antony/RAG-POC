"""Request-scoped AI audit events, attributed only from authenticated server data."""
from contextvars import ContextVar
from datetime import datetime, timezone
import logging

_event_buffer = ContextVar('guardrail_event_buffer', default=None)


def begin_audit(user, conversation_id, access_level):
    events = []
    identity = {
        'user_id': str(user.id),
        'user_name': str((user.user_metadata or {}).get('name') or user.email or user.id),
        'user_email': user.email,
        'user_access': access_level,
        'conversation_id': str(conversation_id),
    }
    return _event_buffer.set((identity, events)), events


def end_audit(token):
    _event_buffer.reset(token)


def record_hit(*, source, rule, action, reason):
    record_event(event_type="guardrail", status=action, source=source,
                 details={"rule": rule, "reason": reason})


def record_event(*, event_type, status="success", source=None, model=None, tool=None, document_id=None, details=None):
    context = _event_buffer.get()

    if context is None:
        return
    identity, events = context

    events.append({
        **identity,
        "event_type": event_type,
        "status": status,
        "source": source,
        "model": model,
        "tool": tool,
        "document_id": document_id,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat(), # UTC storage; the dashboard displays local time.
    })


def persist_hits(database, events):
    if not events:
        return
    try:
        database.table('ai_audit_events').insert(events).execute()
    except Exception:
        # Do not turn a successful chat into an error or expose database details.
        logging.getLogger(__name__).error('Could not persist %d AI audit events; check ai_audit_events migration and database access.', len(events))
