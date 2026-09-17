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
    const detail = data?.detail ?? response.statusText;
    throw new Error(`Backend request failed with status ${response.status}: ${detail}`);
  }

  return data;
}
