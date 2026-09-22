import { File } from 'node:buffer';
import assert from 'node:assert/strict';
import { beforeEach, test } from 'node:test';
import { askQuestion, clearSession, getSession, saveSession, SessionExpiredError, signup, submitPassword, uploadFile } from './api.js';

function storage() {
  const values = new Map();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key) };
}
const session = () => ({ user: { id: 'user-a', name: 'Alex' }, access_token: 'real-token', expires_at: Math.floor(Date.now() / 1000) + 3600 });
beforeEach(() => {
  globalThis.sessionStorage = storage();
  globalThis.localStorage = storage();
});

test('login and signup send credentials without a bearer header', async () => {
  const paths = [];
  globalThis.fetch = async (url, options) => {
    paths.push(new URL(url).pathname);
    assert.equal(options.headers.Authorization, undefined);
    assert.equal(JSON.parse(options.body).password, 'password');
    return new Response(JSON.stringify(session()));
  };
  await submitPassword('alex@example.com', 'password');
  await signup('Alex', 'alex@example.com', 'password');
  assert.deepEqual(paths, ['/login', '/signup']);
});

test('session persists token without password and chat sends standard header', async () => {
  saveSession({ ...session(), password: 'never-save' });
  assert.equal(JSON.stringify(getSession()).includes('never-save'), false);
  globalThis.fetch = async (url, options) => {
    assert.equal(new URL(url).pathname, '/chat');
    assert.equal(options.headers.Authorization, 'Bearer real-token');
    assert.deepEqual(JSON.parse(options.body), { message: 'Question' });
    return new Response(JSON.stringify({ answer: 'Answer' }));
  };
  assert.equal((await askQuestion('Question')).answer, 'Answer');
});

test('uploads use multipart and the saved token', async () => {
  saveSession(session());
  globalThis.fetch = async (url, options) => {
    assert.equal(new URL(url).pathname, '/upload');
    assert.equal(options.headers.Authorization, 'Bearer real-token');
    assert.equal(options.headers['Content-Type'], undefined);
    assert.equal(options.body.get('file').name, 'policy.md');
    return new Response(JSON.stringify({ filename: 'policy.md' }));
  };
  await uploadFile(new File(['Policy'], 'policy.md'));
});

test('401 expires a protected session but invalid login stays a form error', async () => {
  saveSession(session());
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 });
  await assert.rejects(askQuestion('Question'), SessionExpiredError);
  assert.equal(getSession(), null);
  await assert.rejects(submitPassword('alex@example.com', 'bad'), (error) => !(error instanceof SessionExpiredError) && error.message === 'Invalid credentials');
});

test('expired or malformed sessions never send protected requests', async () => {
  globalThis.fetch = async () => assert.fail('Should not send a request');
  sessionStorage.setItem('rag-session', JSON.stringify({ ...session(), expires_at: 1 }));
  await assert.rejects(askQuestion('Question'), SessionExpiredError);
  sessionStorage.setItem('rag-session', 'invalid-json');
  assert.equal(getSession(), null);
});

test('sign out removes current and legacy credentials', () => {
  saveSession(session());
  localStorage.setItem('access_token', 'old-token');
  sessionStorage.setItem('rag-demo-user', '{}');
  clearSession();
  assert.equal(getSession(), null);
  assert.equal(localStorage.getItem('access_token'), null);
  assert.equal(sessionStorage.getItem('rag-demo-user'), null);
});

test('an old request cannot clear a newly signed-in session', async () => {
  saveSession(session());
  let finish;
  globalThis.fetch = () => new Promise((resolve) => { finish = resolve; });
  const pending = askQuestion('Question');
  saveSession({ ...session(), access_token: 'new-token', user: { id: 'user-b', name: 'Sam' } });
  finish(new Response('{}', { status: 401 }));
  await assert.rejects(pending, /previous session/);
  assert.equal(getSession().access_token, 'new-token');
});
