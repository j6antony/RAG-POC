import { useEffect, useRef, useState } from 'react';
import ChatInput from './components/chatinput';
import ChatWindow from './components/chatwindow';
import DocumentPanel from './components/documentpanel';
import AuthPage from './components/authpage';
import { askQuestion, getConversation, getConversationMessages } from './services/api';


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
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(0);
  const busy = useRef(false);
  const activeStream = useRef(null);
  const [progress, setProgress] = useState([]);
  const [conversations, setConversations] = useState()
  
  useEffect(() => () => activeStream.current?.abort(), []);
  useEffect(() => {
    if (!user) return;

    async function loadConversations() {
      try {
        const data = await getConversation();
        setconversations(data)
      } catch (error) {
        console.error ("Failed to load conversations", error);
      }
    }
    loadConversations();
  }, [user]);

 
  async function openConversation(conversation) {
    if (busy.current) return;

    activeStream.current?.abort();
    request.current += 1;

    try {
      const storedMessages = await getConversationMessages(conversation.id);

      setConversationId(conversation.id);

      setMessages(
        storedMessages.map((message) => ({
          id: message.id,
          role: message.role,
          text: message.text,
        }))
      );

      setError(null);
      setProgress([]);

    } catch (error) {
      console.error("Failed to open conversation:", error);
    }
  }

  async function sendMessage(text, retry = false) {
    const question = text.trim();
    if (!question || busy.current) return;
    busy.current = true;
    const currentRequest = ++request.current;
    const controller = new AbortController();
    activeStream.current = controller;
    setProgress([{ stage: 'connecting', message: 'Connecting to the assistant…' }]);
    setPending(true);
    setError(null);
    if (!retry) setMessages((previous) => [...previous, { id: crypto.randomUUID(), role: 'user', text: question }]);
    // this is actually an error as it is always refresshing for new chats rather than letting the backend register the chat and refresh the sidebar when it does need to rework the entire design to fix this though so for now I left it as is
    const updatedConversations = await getConversation();
    setConversations(updatedConversations);
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
        // this is actually an error as it is always refresshing for new chats rather than letting the backend register the chat and refresh the sidebar when it does need to rework the entire design to fix this though so for now I left it as is
      const updatedConversations = await getConversation();
      setConversations(updatedConversations);
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

    setUser(null);
  }

  if (!user) return <AuthPage onContinue={enterWorkspace} />;

  return (
    <div className="app-shell">
      <DocumentPanel />
      <main id="main" className="main-panel">
        <div className="chat-layout">
          <header className="conversation-header"><div><h1>Document chat</h1><p className="account-caption">{user.name} <span>· Demo session</span></p></div><div className="header-actions"><button className="new-chat" onClick={resetChat}>New conversation</button><button className="new-chat" onClick={signOut}>Sign out</button></div></header>
          <ChatWindow messages={messages} pending={pending} progress={progress} failed={Boolean(error)} onSelectQuestion={sendMessage} examples={exampleQuestions} />
          {error && <div className="error-notice" role="alert">{error.text}<button onClick={() => sendMessage(error.question, true)}>Retry</button></div>}
          <div className="composer-area"><ChatInput key={conversationId} onSendMessage={sendMessage} disabled={pending || Boolean(error)} /><p className="disclaimer">Answers come from your local RAG backend.</p></div>
        </div>
      </main>
    </div>
  );
}
