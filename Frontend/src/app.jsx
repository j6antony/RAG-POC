import { useEffect, useRef, useState } from 'react';
import ChatInput from './components/chatinput';
import ChatWindow from './components/chatwindow';
import ConversationSidebar from './components/conversationsidebar';
import GuardrailPage from './components/guardrailpage';
import AuthPage from './components/authpage';
import { askQuestion, getConversation, getConversationMessages, getAccess } from './services/api';


const exampleQuestions = [
  { question: 'How many vacation days do I get?' },
  { question: 'How often can I work remotely?' },
  { question: 'How do I contact IT support?' },
];

export default function App() {
  const [user, setUser] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem('rag-demo-user'));
      const token = localStorage.getItem("access_token");
      return saved && token && typeof saved.name === 'string'
          ? saved
          : null;
    } catch { return null; }
  });
  const [page, setPage] = useState('chat');
  const [accessLevel, setAccessLevel] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(0);
  const busy = useRef(false);
  const activeStream = useRef(null);
  const [progress, setProgress] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [openingId, setOpeningId] = useState(null);
  const historyRequest = useRef(0);

  useEffect(() => () => activeStream.current?.abort(), []);
  useEffect(() => {
    if (user) loadConversations();
    return () => { historyRequest.current += 1; };
  }, [user]);

  useEffect(() => {
    setAccessLevel(null);
    if (!user) return;
    const controller = new AbortController();
    getAccess(controller.signal).then((level) => {
      if (!controller.signal.aborted) setAccessLevel(level);
    }).catch(() => { /* Fail closed: admin navigation requires verified access. */ });
    return () => controller.abort();
  }, [user]);

  async function loadConversations() {
    const current = ++historyRequest.current;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const data = await getConversation();
      if (current === historyRequest.current) setConversations(data);
    } catch (error) {
      if (current === historyRequest.current) setHistoryError(error instanceof Error ? error.message : 'Failed to load conversations.');
    } finally {
      if (current === historyRequest.current) setHistoryLoading(false);
    }
  }

  async function openConversation(conversation) {
    if (busy.current) return;
    const current = ++request.current;
    setOpeningId(conversation.id);
    setError(null);
    try {
      const storedMessages = await getConversationMessages(conversation.id);
      if (current !== request.current) return;
      setConversationId(conversation.id);
      setMessages(storedMessages.map((message) => ({ id: message.id, role: message.role, text: message.text })));
      setProgress([]);
    } catch (error) {
      if (current === request.current) setError({ text: error instanceof Error ? error.message : 'Failed to open conversation.', conversation });
    } finally {
      if (current === request.current) setOpeningId(null);
    }
  }

  async function sendMessage(text, retry = false) {
    const question = text.trim();
    if (!question || busy.current || openingId) return;
    busy.current = true;
    const currentRequest = ++request.current;
    const controller = new AbortController();
    activeStream.current = controller;
    setProgress([{ stage: 'connecting', message: 'Connecting to the assistant…' }]);
    setPending(true);
    setError(null);
    if (!retry) setMessages((previous) => [...previous, { id: crypto.randomUUID(), role: 'user', text: question }]);
    try {
      const result = await askQuestion(question, conversationId, {
        signal: controller.signal,
        onProgress: (event) => {
          if (currentRequest !== request.current) return;
          setProgress((previous) => [...previous, event]);
        },
      });
      if (currentRequest !== request.current) return;
      if (typeof result.answer !== 'string') throw new Error('Invalid response');
      setMessages((previous) => [...previous, { id: crypto.randomUUID(), role: 'assistant', text: result.answer, sources: result.sources ?? [], images: result.images ?? [] }]);
      // History errors should not mark an already delivered answer as failed.
      void loadConversations();
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
        activeStream.current = null;
        setPending(false);
      }
    }
  }

  function resetChat() {
    activeStream.current?.abort();
    activeStream.current = null;
    setProgress([]);
    setOpeningId(null);
    setConversationId(crypto.randomUUID());
    request.current += 1;
    busy.current = false;
    setMessages([]);
    setPending(false);
    setError(null);
  }

  function enterWorkspace(profile) {
    try { sessionStorage.setItem('rag-demo-user', JSON.stringify(profile)); } catch { /* Session can work in memory. */ }
    setUser(profile);
  }

  function signOut() {
    resetChat();


    try { sessionStorage.removeItem('rag-demo-user'); } catch { /* Storage may be unavailable. */ }

    localStorage.removeItem("access_token");

    historyRequest.current += 1;
    setConversations([]);
    setHistoryError(null);
    setAccessLevel(null);
    setPage('chat');
    setUser(null);
  }

  if (!user) return <AuthPage onContinue={enterWorkspace} />;

  if (page === 'guardrails' && accessLevel === 3) return <GuardrailPage onBack={() => setPage('chat')} onSignOut={signOut} />;

  return (
    <div className="app-shell">
      <ConversationSidebar conversations={conversations} activeId={conversationId} loading={historyLoading} error={historyError} openingId={openingId} disabled={pending} onOpen={openConversation} onNew={resetChat} onRefresh={loadConversations} />
      <main id="main" className="main-panel">
        <div className="chat-layout">
          <header className="conversation-header"><div><h1>Document chat</h1><p className="account-caption">{user.name} <span>· Demo session</span></p></div><div className="header-actions">{accessLevel === 3 && <button className="new-chat" onClick={() => setPage('guardrails')}>AI Governance</button>}<button className="new-chat" onClick={resetChat}>New conversation</button><button className="new-chat" onClick={signOut}>Sign out</button></div></header>
          {openingId && <p className="document-status" role="status">Opening conversation…</p>}
          <ChatWindow messages={messages} pending={pending} progress={progress} failed={Boolean(error)} onSelectQuestion={sendMessage} examples={exampleQuestions} />
          {error && <div className="error-notice" role="alert">{error.text}<button onClick={() => error.conversation ? openConversation(error.conversation) : sendMessage(error.question, true)}>Retry</button></div>}
          <div className="composer-area"><ChatInput key={conversationId} onSendMessage={sendMessage} disabled={pending || Boolean(openingId)} /><p className="disclaimer">Answers come from your local RAG backend.</p></div>
        </div>
      </main>
    </div>
  );
}
