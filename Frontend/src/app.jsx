import { useRef, useState } from 'react';
import ChatInput from './components/chatinput';
import ChatWindow from './components/chatwindow';
import { askQuestion } from './services/api';

const exampleQuestions = [
  { question: 'How many vacation days do I get?' },
  { question: 'How often can I work remotely?' },
  { question: 'How do I contact IT support?' },
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(0);
  const busy = useRef(false);

  async function sendMessage(text, retry = false) {
    const question = text.trim();
    if (!question || busy.current) return;
    busy.current = true;
    const currentRequest = ++request.current;
    setPending(true);
    setError(null);
    if (!retry) setMessages((previous) => [...previous, { id: crypto.randomUUID(), role: 'user', text: question }]);
    try {
      const result = await askQuestion(question);
      if (currentRequest !== request.current) return;
      if (typeof result.answer !== 'string') throw new Error('Invalid response');
      setMessages((previous) => [...previous, { id: crypto.randomUUID(), role: 'assistant', text: result.answer, sources: result.sources ?? [] }]);
    } catch (error) {
      console.error(error);
      if (currentRequest === request.current) {
        setError({
          question,
          text: error instanceof Error ? error.message : 'Something went wrong. Please try your question again.',
        });
      }
    } finally {
      if (currentRequest === request.current) {
        busy.current = false;
        setPending(false);
      }
    }
  }

  function resetChat() {
    setConversationId((previous) => previous + 1);
    request.current += 1;
    busy.current = false;
    setMessages([]);
    setPending(false);
    setError(null);
  }

  return (
    <div className="app-shell">
      <main id="main" className="main-panel">
        <div className="chat-layout">
          <header className="conversation-header"><h1>Document chat</h1><button className="new-chat" onClick={resetChat}>New conversation</button></header>
          <ChatWindow messages={messages} pending={pending} onSelectQuestion={sendMessage} examples={exampleQuestions} />
          {error && <div className="error-notice" role="alert">{error.text}<button onClick={() => sendMessage(error.question, true)}>Retry</button></div>}
          <div className="composer-area"><ChatInput key={conversationId} onSendMessage={sendMessage} disabled={pending || Boolean(error)} /><p className="disclaimer">Answers come from your local RAG backend.</p></div>
        </div>
      </main>
    </div>
  );
}
