import { resolvePath } from "react-router-dom";

// Contract: askQuestion(question) -> { answer, sources: [{ title, section, text }] }
export async function askQuestion(question) {
  const response = await fetch('http://127.0.0.1:8000/chat', {
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
  const formData = new formData();

  formData.append("file", file)

  const response = await fetch('http://127.0.0.1:8000/upload', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json().catch(()=>null);

  if (!response.ok){
    throw new Error("File upload failed");
  }
  return data;
}

export async function getFiles() {
  const response = await fetch('http://127.0.0.1:8000/upload');

  const data = await response.json().catch(()=>null);

  if (!response.ok) {
    throw new Error("Could not load available files")
  };

  return data.files;
}