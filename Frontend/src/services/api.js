const apiUrl = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'rag-session';

export function clearSession() {
  sessionStorage.removeItem(sessionKey);
  sessionStorage.removeItem('rag-demo-user');
  localStorage.removeItem('access_token');
}

export function getSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(sessionKey));
    if (!session?.access_token || !session?.user?.id || !session?.user?.name ||
        !Number.isFinite(session.expires_at) || session.expires_at * 1000 <= Date.now()) {
      return null;
    }
    return session;
  } catch { return null; }
}

export function saveSession(result) {
  if (!result?.access_token || !result?.user?.id || !result?.user?.name ||
      !Number.isFinite(result.expires_at) || result.expires_at * 1000 <= Date.now()) {
    throw new Error('The server returned an incomplete session. Please log in again.');
  }
  clearSession();
  sessionStorage.setItem(sessionKey, JSON.stringify({
    user: result.user, access_token: result.access_token, expires_at: result.expires_at,
  }));
}

export class SessionExpiredError extends Error {}

async function request(path, { body, authenticated = false } = {}) {
  const headers = {};
  if (authenticated) {
    const session = getSession();
    if (!session) {
      clearSession();
      throw new SessionExpiredError('Your session has expired. Please log in again.');
    }
    headers.Authorization = `Bearer ${session.access_token}`;
  }
  if (!(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method: 'POST', headers,
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  } catch {
    throw new Error('Could not reach the server. Check your connection and try again.');
  }
  const data = await response.json().catch(() => null);
  if (authenticated && response.status === 401) {
    const currentSession = getSession();
    if (!currentSession || currentSession.access_token === headers.Authorization.slice(7)) {
      clearSession();
      throw new SessionExpiredError('Your session has expired. Please log in again.');
    }
    throw new Error('This request belongs to a previous session.');
  }
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail
      : Array.isArray(data?.detail) ? data.detail.map((item) => item.msg).join(' ')
      : `Request failed (${response.status}). Please try again.`;
    throw new Error(detail);
  }
  if (!data) throw new Error('The server returned an invalid response. Please try again.');
  return data;
}

export function askQuestion(question) {
  return request('/chat', { body: { message: question }, authenticated: true });
}

export function uploadFile(file) {
  const body = new FormData();
  body.append('file', file);
  return request('/upload', { body, authenticated: true });
}

export function submitPassword(email, password) {
  return request('/login', { body: { email, password } });
}

export function signup(name, email, password) {
  return request('/signup', { body: { name, email, password } });
}
