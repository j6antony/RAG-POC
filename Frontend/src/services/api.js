// Contract: askQuestion(question) -> { answer, sources: [{ title, section, text }] }
const api_url = import.meta.env.VITE.api_url || "http://127.0.0.1:8000"

export async function askQuestion(question) {
  const response = await fetch('${api_url}/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: question }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // The question marks are like a wierd way of chaining conditional statements
    const detail = data?.detail ?? response.statusText;
    throw new Error(`Backend request failed with status ${response.status}: ${detail}`);
  }

  return data;
}

export async function uploadFile(file) {
  // the reason we need to use a formdata here is becuase unlike with text, numbers and stuff you cannot just stringify the json here with files
  const formData = new FormData();

  formData.append("file", file)

  const response = await fetch('${api_url}/upload', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json().catch(()=>null);

  if (!response.ok){
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'File upload failed. Please try again.');
  }
  return data;
}

export async function getFiles() {
  const response = await fetch('${api_url}/files', {
    method: "GET"
  });

  const data = await response.json().catch(()=>null);

  if (!response.ok) {
    throw new Error("Could not load available files")
  };

  if (!Array.isArray(data?.files) || !data.files.every((file) => typeof file === 'string')) {
    throw new Error('The backend returned an invalid document list.');
  }
  return [...new Set(data.files)].sort((a, b) => a.localeCompare(b));
}