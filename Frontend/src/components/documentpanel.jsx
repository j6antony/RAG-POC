import { useRef, useState } from 'react';
import { uploadFile } from '../services/api';
import { ACCESS_LEVELS } from '../accesslevels';

export default function DocumentPanel() {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [notice, setNotice] = useState('');
  const [accessLevel, setAccessLevel] = useState(1);
  const input = useRef(null);

  async function handleUpload(event) {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setNotice('');

    try {
      await uploadFile(file, accessLevel);
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

      <label className="document-access" htmlFor="document-access">
        File access level
        <select
          id="document-access"
          value={accessLevel}
          onChange={(event) => setAccessLevel(Number(event.target.value))}
          disabled={uploading}
        >
          {ACCESS_LEVELS.map(({ role, label, level }) => <option key={role} value={level}>{label}</option>)}
        </select>
      </label>

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
