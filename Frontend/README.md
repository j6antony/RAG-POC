# Document chat frontend

React + Vite interface connected to the FastAPI backend.

```sh
npm ci
npm run dev
```

The backend defaults to `http://127.0.0.1:8000`. Set `VITE_API_URL` in `Frontend/.env` to override it, then restart Vite (or rebuild for production).

- Login and signup use Supabase through the backend, including email-confirmation notices.
- The access token and profile stay in session storage for this tab. Expired sessions return to login; sign out clears credentials and the conversation.
- Upload Markdown or text with the header button. Files are indexed into Pinecone; no local file list is shown.
- Chat sends a bearer token and shows actual source excerpts when returned by the backend.
- Enter sends a question; Shift + Enter inserts a newline. New conversation resets the chat.

`npm test` runs the API/session regression tests. `npm run build` creates the production build, and `npm run preview` serves it locally. See the root README for backend configuration and current limitations.
