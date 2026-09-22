// Contract: askQuestion(question) -> { answer, sources: [{ title, section, text }] }
const api_url = "http://127.0.0.1:8000";
// this would not work becuase token capture to early 
//const token = localStorage.getItem("access_token");


export async function askQuestion(question,history) {
  const response = await fetch(`${api_url}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Autherization': `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ message: question, history: history.slice(-6)}),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // The question marks are like a wierd way of chaining conditional statements
    const detail = data?.detail ?? response.statusText;
    throw new Error(`Backend request failed with status ${response.status}: ${detail}`);
  }

  return data;
}

function getToken() {
  return localStorage.getItem("access_token");
}
export async function uploadFile(file) {
  // the reason we need to use a formdata here is becuase unlike with text, numbers and stuff you cannot just stringify the json here with files
  const formData = new FormData();

  formData.append("file", file)

  const response = await fetch(`${api_url}/upload`, {
    method: 'POST',
    headers: {'Autherization': `Bearer ${getToken()}`,},
    body: formData,
  });

  const data = await response.json().catch(()=>null);

  if (!response.ok){
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'File upload failed. Please try again.');
  }
  return data;
}

export async function submitPassword(email, password) {
  const response = await fetch(`${api_url}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({email, password}),
  });
  const data = await response.json().catch(()=>null);
  if (!response.ok) {
    throw new Error ("incorrect email or password")
  };
  return data;
}

export async function signup(name, email, password) {
  const response = await fetch(`${api_url}/signup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({name, email, password}),
  });
  const data = await response.json().catch(()=>null);
  if (!response.ok) {
    throw new Error ("incorrect signup information")
  };
  return data;
}