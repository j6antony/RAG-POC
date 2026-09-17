import { useEffect, useRef } from 'react';
import Message from './message';

export default function ChatWindow({ messages, pending, onSelectQuestion, examples }) {
  const bottom = useRef(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages, pending]);

  return (
    <section className="chat-window" aria-label="Conversation">
      {!messages.length ? <div className="empty-state">
        <h2>Ask a question</h2>
        <p>Type below or try an example.</p>
        <div className="suggestions">{examples.map((example) => <button key={example.question} onClick={() => onSelectQuestion(example.question)}><span>{example.question}</span></button>)}</div>
      </div> : <div className="messages" role="log" aria-live="polite" aria-relevant="additions">{messages.map((message) => <Message key={message.id} {...message} />)}</div>}
      {pending && <div className="thinking" role="status">Searching documents<span className="loading-dots" aria-hidden="true">•••</span></div>}
      <div ref={bottom} />
    </section>
  );
}
