import { useRef, useState } from 'react';
import { uploadFile } from '../services/api';

export default function DocumentPanel() {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [notice, setNotice] = useState('');
  const input = useRef(null);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setNotice('');

    try {
      await uploadFile(file);
      setNotice(`Uploaded ${file.name}.`);
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

      <button
        className="upload-button"
        disabled={uploading}
        onClick={() => input.current?.click()}
      >
        {uploading ? 'Uploading…' : '+ Upload document'}
      </button>

      <input
        ref={input}
        type="file"
        onChange={handleUpload}
        disabled={uploading}
        hidden
      />

      {uploadError && (
        <p className="document-error">
          {uploadError}
        </p>
      )}

      {notice && (
        <p className="document-status">
          {notice}
        </p>
      )}
    </aside>
  );
}