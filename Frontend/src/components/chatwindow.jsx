import { useEffect, useRef } from 'react';
import Message from './message';

export default function ChatWindow({ messages, pending, progress = [], failed = false, onSelectQuestion, examples }) {
  const bottom = useRef(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, pending, progress]);

  return (
    <section className="chat-window" aria-label="Conversation">
      {!messages.length ? <div className="empty-state">
        <h2>Ask a question</h2>
      </div> : <div className="messages" role="log" aria-live="polite" aria-relevant="additions">{messages.map((message) => <Message key={message.id} {...message} />)}</div>}
      {progress.length > 0 && <div className="chat-progress" aria-label="Request progress">
        <p className="thinking" role="status" aria-live="polite">
          {pending ? progress.at(-1).message : failed ? 'Request interrupted' : 'Response complete'}
          {pending && <span className="loading-dots" aria-hidden="true"> •••</span>}
        </p>
        <details>
          <summary>View progress · {progress.length} updates</summary>
          <ol>{progress.map((event, index) => <li key={index} aria-current={pending && index === progress.length - 1 ? 'step' : undefined}>{event.message}</li>)}</ol>
        </details>
      </div>}
      <div ref={bottom} />
    </section>
  );
}
