import { useEffect, useRef, useState } from 'react';
import { uploadFile, getKnowledge } from '../services/api';
import { ACCESS_LEVELS } from '../accesslevels';

export default function DocumentPanel() {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [notice, setNotice] = useState('');
  const [accessLevel, setAccessLevel] = useState(1);
  const input = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [userAccess, setUserAccess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const loadRequest = useRef(0);

  async function loadKnowledge() {
    const requestId = ++loadRequest.current;
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getKnowledge();
      if (requestId !== loadRequest.current) return;
      setDocuments(data.documents);
      setUserAccess(data.access_level);
      setAccessLevel((level) => Math.min(level, data.access_level));
    } catch (error) {
      if (requestId !== loadRequest.current) return;
      setDocuments([]);
      setUserAccess(null);
      setLoadError(error instanceof Error ? error.message : 'Failed to load knowledge base.');
    } finally {
      if (requestId === loadRequest.current) setLoading(false);
    }
  }

  useEffect(() => {
    loadKnowledge();
    return () => { loadRequest.current += 1; };
  }, []);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file || uploading || !userAccess) return;

    setUploading(true);
    setUploadError(null);
    setNotice('');

    try {
      await uploadFile(file, accessLevel);
      setNotice(`Uploaded ${file.name}.`);
      await loadKnowledge();
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : 'Upload failed. Please try again.'
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <aside className="document-panel">
      <h2>Knowledge Base</h2>

      <label className="document-access" htmlFor="document-access">
        File access level
        <select
          id="document-access"
          value={accessLevel}
          onChange={(event) => setAccessLevel(Number(event.target.value))}
          disabled={uploading || loading || !userAccess}
        >
          {ACCESS_LEVELS.filter(({ level }) => level <= (userAccess ?? 1)).map(({ role, level }) => <option key={role} value={level}>Level {level}</option>)}
        </select>
      </label>

      <p className="document-status">{userAccess ? `Your access: Level ${userAccess}. ` : ''}You can see lower-level documents and your own documents at your level.</p>

      <button
        className="upload-button"
        disabled={uploading || loading || !userAccess}
        onClick={() => input.current?.click()}
      >
        {uploading ? 'Uploading…' : '+ Upload document'}
      </button>

      <input
        ref={input}
        type="file"
        accept=".pdf,.md,.txt,application/pdf,text/plain,text/markdown"
        onChange={handleUpload}
        disabled={uploading || loading || !userAccess}
        hidden
      />

      <p className="document-status">PDF, Markdown, and text files · Up to 20 MB</p>

      <section className="document-list" aria-label="Available documents" aria-busy={loading}>
        <div className="document-list-header">
          <h3>Documents <span>{documents.length}</span></h3>
          <button className="refresh-files" onClick={loadKnowledge} disabled={loading || uploading}>Refresh</button>
        </div>
        {loading && <p className="document-status" role="status">Loading documents…</p>}
        {loadError && <div className="document-error" role="alert"><p>{loadError}</p><button onClick={loadKnowledge}>Retry</button></div>}
        {!loading && !loadError && documents.length === 0 && <p className="document-status">No documents available yet. Upload a document to get started.</p>}
        {!loadError && <ul>{documents.map((document) => (
          <li className="document-item" key={document.id}>
            <span aria-hidden="true">▤</span>
            <span><strong>{document.filename}</strong><small>Level {document.access_level}</small>
              {document.created_at && !Number.isNaN(Date.parse(document.created_at)) && <time dateTime={document.created_at}>{new Date(document.created_at).toLocaleDateString()}</time>}
            </span>
          </li>
        ))}</ul>}
      </section>

      {uploadError && (
        <p className="document-error" role="alert">
          {uploadError}
        </p>
      )}

      {notice && (
        <p className="document-status" role="status">
          {notice}
        </p>
      )}
    </aside>
  );
}
