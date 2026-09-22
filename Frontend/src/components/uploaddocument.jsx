import { useEffect, useRef, useState } from 'react';
import { SessionExpiredError, uploadFile } from '../services/api';

export default function UploadDocument({ onSessionExpired }) {
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const input = useRef(null);
  const busy = useRef(false);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || busy.current) return;
    if (!/\.(md|txt)$/i.test(file.name) || file.size > 5 * 1024 * 1024) {
      setFeedback({ error: true, text: 'Choose a Markdown or text file, 5 MB or smaller.' });
      return;
    }
    busy.current = true;
    setUploading(true);
    setFeedback(null);
    try {
      await uploadFile(file);
      if (!mounted.current) return;
      setFeedback({ text: `Indexed ${file.name}. It may take a few seconds to appear in search.` });
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof SessionExpiredError) onSessionExpired(error.message);
      else setFeedback({ error: true, text: error.message });
    } finally {
      busy.current = false;
      setUploading(false);
    }
  }

  return <div className="upload-control">
    <button className="new-chat" disabled={uploading} onClick={() => input.current?.click()}>{uploading ? 'Uploading…' : '+ Upload document'}</button>
    <input ref={input} type="file" accept=".md,.txt" aria-label="Upload document" onChange={handleUpload} disabled={uploading} hidden />
    {feedback && <div className="upload-feedback" role={feedback.error ? 'alert' : 'status'}><p>{feedback.text}</p><button onClick={() => setFeedback(null)}>Dismiss</button></div>}
  </div>;
}
