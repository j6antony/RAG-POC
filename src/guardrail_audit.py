"""Request-scoped guardrail events, attributed only from authenticated server data."""
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
    context = _event_buffer.get()
    if context is None:
        return
    identity, events = context
    # Store rule metadata, not prompts, credentials, or retrieved document bodies.
    events.append({**identity, 'source': source, 'rule': rule, 'action': action,
                   'reason': reason, 'created_at': datetime.now(timezone.utc).isoformat()})


def persist_hits(database, events):
    if not events:
        return
    try:
        database.table('guardrail_events').insert(events).execute()
    except Exception:
        # Do not turn a successful chat into an error or expose database details.
        logging.getLogger(__name__).error('Could not persist %d guardrail events; check guardrail_events migration and database access.', len(events))
