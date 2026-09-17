import { useRef, useState } from 'react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [message, setMessage] = useState('');
  const input = useRef(null);
  function handleSubmit(event) {
    event.preventDefault();
    if (disabled || !message.trim()) return;
    onSendMessage(message.trim());
    setMessage('');
    input.current?.focus();
  }
  return <form className="composer" onSubmit={handleSubmit}>
    <label className="sr-only" htmlFor="question">Ask a question about your documents</label>
    <textarea ref={input} id="question" rows={2} placeholder="Ask a question about your documents…" value={message} maxLength={4000} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) handleSubmit(event); }} />
    <div className="composer-bottom"><span>↵ <span>Enter to send</span><span className="shift-hint"> · Shift + Enter for a new line</span></span><button type="submit" disabled={disabled || !message.trim()} aria-label="Send question">↑</button></div>
  </form>;
}
