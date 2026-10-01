import KnowledgeImage from './knowledgeimage';

export default function Message({ role, text, sources = [], images = [] }) {
  const isUser = role === 'user';
  return <article className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
    <div className="message-content"><div className="message-label">{isUser ? 'You' : 'Assistant'}</div><p>{text}</p>
      {!isUser && images.length > 0 && <section className="knowledge-images" aria-label="Images from retrieved pages"><h3>Images from retrieved pages</h3>{images.map((image) => <KnowledgeImage key={image.id} image={image} />)}</section>}
      {sources.length > 0 && <div className="sources"><div className="source-label">EXAMPLE SOURCES · {sources.length}</div>{sources.map((source, index) => <details key={`${source.title}-${index}`}><summary><span aria-hidden="true">▤</span><span>{source.title}<small>{source.section}</small></span><span className="source-expand" aria-hidden="true">＋</span></summary><blockquote>{source.text}</blockquote></details>)}</div>}
    </div>
  </article>;
}
