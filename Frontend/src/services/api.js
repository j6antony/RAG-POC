import { readChatStream } from './sse.js';

const api_url = "http://127.0.0.1:8000";

export async function askQuestion(question, conversationId, { onProgress, signal } = {}) {
  const response = await fetch(`${api_url}/chat`, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Autherization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ message: question, conversation_id: conversationId }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = typeof data?.detail === 'string' ? data.detail : response.statusText;
    throw new Error(`Backend request failed with status ${response.status}: ${detail}`);
  }
  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    return readChatStream(response.body, onProgress);
  }
  // Keep compatibility with a backend still returning the previous JSON contract.
  const data = await response.json();
  if (typeof data?.answer !== 'string') throw new Error('Invalid backend response.');
  return data;
}

function getToken() {
  return localStorage.getItem("access_token");
}
export async function uploadFile(file, accessLevel = 1, classification = 'internal', containsSensitiveData = false) {
  // the reason we need to use a formdata here is becuase unlike with text, numbers and stuff you cannot just stringify the json here with files
  const formData = new FormData();

  formData.append("file", file);
  formData.append("access_level", String(accessLevel));
  formData.append("classification", String(classification));
  formData.append("contains_sensitive_data", String(containsSensitiveData));

  const response = await fetch(`${api_url}/upload`, {
    method: 'POST',
    headers: {'Autherization': `Bearer ${getToken()}`,},
    body: formData,
  });

  const data = await response.json().catch(()=>null);

  if (!response.ok){
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'File upload failed. Please try again.');
  }
  return data;
}

export async function submitPassword(email, password) {
  const response = await fetch(`${api_url}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({email, password}),
  });
  const data = await response.json().catch(()=>null);
  if (!response.ok) {
    throw new Error ("incorrect email or password")
  };
  return data;
}

export async function signup(name, email, password, role = 'user') {
  const response = await fetch(`${api_url}/signup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({name, email, password, role}),
  });
  const data = await response.json().catch(()=>null);
  if (!response.ok) {
    throw new Error ("incorrect signup information")
  };
  return data;
}

export async function getKnowledge() {

  const response = await fetch(
    `${api_url}/knowledge`,
    {
      method: 'GET',

      headers: {
        'Autherization': `Bearer ${getToken()}`,
      }
    }
  );

  const data = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Failed to load knowledge base.'
    );
  }

  if (!Array.isArray(data?.documents) || ![1, 2, 3].includes(data.access_level)) {
    throw new Error('Invalid knowledge base response.');
  }
  return data;
}

export async function getKnowledgeImage(imageId, signal) {
  const response = await fetch(`${api_url}/knowledge/images/${encodeURIComponent(imageId)}`, {
    headers: { Autherization: `Bearer ${getToken()}` }, signal,
  });
  if (!response.ok) throw new Error('Image unavailable or access has changed.');
  return response.blob();
}
// api functions for history

export async function getConversation() {
  const response = await fetch(`${api_url}/conversations`, {
    headers: {
      Autherization: `Bearer ${getToken()}`,
    },
  });
  const data = await response.json().catch(()=>null);

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Failed to load conversation'
    );
  }
  if (!Array.isArray(data?.conversations)) throw new Error('Invalid conversation history response.');
  return data.conversations;
}

export async function getConversationMessages(conversationId) {
  const response = await fetch(
    `${api_url}/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      headers: {
        Autherization:  `Bearer ${getToken()}`,
      },
    }
  );
  const data = await response.json().catch(()=>null);

  if (!response.ok) {
    throw new Error (
      typeof data?.detail === 'string'
        ? data.detail
        : 'Failed to load conversation.'
    );
  }

  if (!Array.isArray(data?.messages)) throw new Error('Invalid conversation messages response.');
  return data.messages;
  
}

export async function getAccess(signal) {
  const response = await fetch(`${api_url}/me/access`, { headers: { Autherization: `Bearer ${getToken()}` }, signal });
  const data = await response.json().catch(() => null);
  if (!response.ok || ![1, 2, 3].includes(data?.access_level)) throw new Error('Unable to verify account access.');
  return data.access_level;
}

export async function getAuditEvents({ offset = 0, eventType = '', status = '', signal } = {}) {
  const params = new URLSearchParams({ offset: String(offset), limit: '25' });
  if (eventType) params.set('event_type', eventType);
  if (status) params.set('status', status);
  const response = await fetch(`${api_url}/admin/audit-events?${params}`, { headers: { Autherization: `Bearer ${getToken()}` }, signal });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || 'Unable to load AI audit events.');
  if (!Array.isArray(data?.events) || typeof data.has_more !== 'boolean') throw new Error('Invalid AI audit events response.');
  return data;
}
