// Read SSE over POST so chat can keep its JSON body and authentication header.
export async function readChatStream(body, onProgress = () => {}) {
  if (!body) throw new Error('The backend returned an empty stream.');
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let event = '';
  let data = [];
  let result;

  function dispatch() {
    const type = event;
    const payload = data.join('\n');
    event = '';
    data = [];
    if (!payload || !['progress', 'complete', 'error'].includes(type)) return;
    let value;
    try { value = JSON.parse(payload); }
    catch { throw new Error('The backend sent an invalid stream event.'); }
    if (type === 'error') throw new Error(value?.message || 'The backend could not complete the request.');
    if (type === 'progress') {
      if (typeof value?.message === 'string') onProgress(value);
    } else {
      if (typeof value?.answer !== 'string') throw new Error('The backend sent an invalid final answer.');
      result = value;
    }
  }

  function consumeLine(line) {
    if (line === '') return dispatch();
    if (line.startsWith(':')) return; // Heartbeats/comments.
    const colon = line.indexOf(':');
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') event = value;
    if (field === 'data') data.push(value);
  }

  try {
    while (result === undefined) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let match;
      while ((match = /\r\n|\r|\n/.exec(buffer))) {
        // A CRLF can be split across network reads.
        if (!done && match[0] === '\r' && match.index === buffer.length - 1) break;
        const line = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);
        consumeLine(line);
        if (result !== undefined) return result;
      }
      if (done) throw new Error('The connection closed before the answer finished. Please retry.');
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
