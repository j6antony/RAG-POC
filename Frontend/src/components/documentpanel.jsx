import { useEffect, useRef, useState } from 'react';
import { getFiles, uploadFile } from '../services/api';

export default function DocumentPanel() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [listError, setListError] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [notice, setNotice] = useState('');
  const input = useRef(null);
  const busy = useRef(false);

  async function loadFiles() {
    setLoading(true);
    setListError(null);
    try {
      setFiles(await getFiles());
    } catch (error) {
      setListError(error instanceof Error ? error.message : 'Could not load documents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadFiles(); }, []);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || busy.current) return;
    busy.current = true;
    setUploading(true);
    setUploadError(null);
    setNotice('');
    try {
      await uploadFile(file);
      setNotice(`Uploaded ${file.name}.`);
      await loadFiles();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed. Please try again.');
    } finally {
      busy.current = false;
      setUploading(false);
    }
  }

  return (
    <aside className="document-panel" aria-labelledby="knowledge-base-title">
      <h2 id="knowledge-base-title">Knowledge Base</h2>
      <button className="upload-button" disabled={uploading || loading} onClick={() => input.current?.click()}>
        {uploading ? 'Uploading…' : '+ Upload document'}
      </button>
      <input ref={input} type="file" aria-label="Upload document" onChange={handleUpload} disabled={uploading || loading} hidden />
      <div className="document-list" aria-busy={loading}>
        <div className="document-list-header">
          <h3>Documents <span>{files.length}</span></h3>
          <button className="refresh-files" onClick={loadFiles} disabled={loading || uploading} aria-label="Refresh documents">Refresh</button>
        </div>
        {loading && <p className="document-status" role="status">Loading documents…</p>}
        {!loading && !listError && files.length === 0 && <p className="document-status">No documents yet. Upload a file to get started.</p>}
        {files.length > 0 && <ul>{files.map((file) => (
          <li className="document-item" key={file}><span aria-hidden="true">▤</span><span>{file}</span></li>
        ))}</ul>}
        {listError && <div className="document-error" role="alert"><p>{listError}</p><button onClick={loadFiles} disabled={loading || uploading}>Retry</button></div>}
      </div>
      {uploadError && <p className="document-error" role="alert">{uploadError}</p>}
      <p className="document-status upload-status" role="status">{uploading ? 'Uploading your document…' : notice}</p>
    </aside>
  );
}
