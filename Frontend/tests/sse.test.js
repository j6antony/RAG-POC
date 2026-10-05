import test from 'node:test';
import assert from 'node:assert/strict';
import { readChatStream } from '../src/services/sse.js';
import { askQuestion } from '../src/services/api.js';

const encode = (text) => new TextEncoder().encode(text);
function stream(text, split = false) {
  const bytes = encode(text);
  return new ReadableStream({ start(controller) {
    if (split) for (const byte of bytes) controller.enqueue(Uint8Array.of(byte));
    else controller.enqueue(bytes);
    controller.close();
  } });
}

test('handles byte-split UTF-8, CRLF, multiline data, comments, and complete payload', async () => {
  const updates = [];
  const body = stream(': heartbeat\r\nevent: progress\r\ndata: {"stage":"search_web",\r\ndata: "message":"Searching…"}\r\n\r\nevent: complete\r\ndata: {"answer":"Café", "images":[{"id":"image"}], "sources":[]}\r\n\r\n', true);
  const result = await readChatStream(body, (event) => updates.push(event));
  assert.deepEqual(updates, [{stage: 'search_web', message: 'Searching…'}]);
  assert.equal(result.answer, 'Café');
  assert.equal(result.images[0].id, 'image');
});

test('delivers progress before the server completes', async () => {
  let controller;
  let notify;
  const progressReceived = new Promise((resolve) => { notify = resolve; });
  const result = readChatStream(new ReadableStream({ start(c) { controller = c; } }), notify);
  controller.enqueue(encode('event: progress\ndata: {"message":"Using an agent"}\n\n'));
  assert.equal((await progressReceived).message, 'Using an agent');
  controller.enqueue(encode('event: complete\ndata: {"answer":"Done"}\n\n'));
  assert.equal((await result).answer, 'Done');
});

test('reports backend errors and truncated streams', async () => {
  await assert.rejects(readChatStream(stream('event: error\ndata: {"message":"Agent unavailable"}\n\n')), /Agent unavailable/);
  await assert.rejects(readChatStream(stream('event: progress\ndata: {"message":"Working"}\n\n')), /connection closed/);
  await assert.rejects(readChatStream(stream('event: complete\ndata: invalid\n\n')), /invalid stream event/);
  await assert.rejects(readChatStream(stream('event: complete\ndata: {}\n\n')), /invalid final answer/);
});

test('preserves POST authentication, progress, HTTP errors, JSON compatibility and abort signal', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.method, 'POST');
    assert.equal(options.headers.Autherization, 'Bearer test');
    assert.equal(options.headers.Accept, 'text/event-stream');
    assert.equal(JSON.parse(options.body).conversation_id, 'conversation');
    assert.ok(options.signal);
    return new Response(stream('event: complete\ndata: {"answer":"Done"}\n\n'), { headers: {'Content-Type': 'text/event-stream'} });
  });
  const original = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => 'test' };
  t.after(() => { if (original === undefined) delete globalThis.localStorage; else globalThis.localStorage = original; });
  assert.equal((await askQuestion('Hello', 'conversation', {signal: new AbortController().signal})).answer, 'Done');
  globalThis.fetch.mock.mockImplementation(async () => new Response(JSON.stringify({detail:'Expired token'}), {status:401}));
  await assert.rejects(askQuestion('Hello', 'conversation'), /Expired token/);
  globalThis.fetch.mock.mockImplementation(async () => new Response(JSON.stringify({answer:'Legacy answer'}), {headers:{'Content-Type':'application/json'}}));
  assert.equal((await askQuestion('Hello', 'conversation')).answer, 'Legacy answer');
});

test('propagates cancellation rather than reporting completion', async () => {
  const body = new ReadableStream({ start(controller) { controller.error(new DOMException('Aborted', 'AbortError')); } });
  await assert.rejects(readChatStream(body), {name:'AbortError'});
});
