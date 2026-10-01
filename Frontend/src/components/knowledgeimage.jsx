import { useEffect, useState } from 'react';
import { getKnowledgeImage } from '../services/api';

export default function KnowledgeImage({ image }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    setUrl(null);
    setError('');
    getKnowledgeImage(image.id, controller.signal).then((blob) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    }).catch((error) => {
      if (!controller.signal.aborted) setError(error.message);
    });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [image.id, attempt]);
  return <figure className="knowledge-image">
    {url ? <a href={url} target="_blank" rel="noreferrer"><img src={url} alt={`Extracted image from ${image.filename}, page ${image.page_number}`} onError={() => { setUrl(null); setError('Could not display this image.'); }} /></a>
      : error ? <p role="alert">{error} <button onClick={() => setAttempt(attempt + 1)}>Retry</button></p>
      : <p role="status">Loading image…</p>}
    <figcaption>{image.filename} · Page {image.page_number}</figcaption>
  </figure>;
}
