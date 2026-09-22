# RAG chat frontend

A React + Vite chat interface for the RAG proof of concept. Runs independently of the Python backend.

## Run

```sh
cd Frontend
npm install
npm run dev
```

`npm run build` creates a production build; `npm run preview` previews it.

## Current behavior

- Send questions with Enter or the send button; Shift + Enter adds a line break.
- The three example questions return preset answers and expandable excerpts from the repository's sample documents.
- Other questions receive a clear demo placeholder. No retrieval, LLM calls, uploads, or backend requests run.
- New conversation clears the current session, including any pending demo response. History is in memory and clears on refresh.
- Loading, empty, and retry states are included. The demo adapter always succeeds; retry is available for future service failures.

## Connect a backend later

Replace `askQuestion` in `src/services/api.js` with your API call. It accepts a question string and returns:

```js
{
  answer: 'Answer text',
  sources: [{ title: 'document.md', section: 'Section name', text: 'Source excerpt' }]
}
```

Sources are optional. Throw on HTTP or response errors so the chat can display Retry. Once live integration is implemented, update the demo labels in `app.jsx`, `chatwindow.jsx`, and `message.jsx`. Keep API keys on the backend.
