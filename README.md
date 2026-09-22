# Document chat — RAG proof of concept

React + FastAPI with Supabase authentication, Pinecone vector search, and Gemini answers.

## Flow

1. Sign up or log in with Supabase. If email confirmation is enabled, confirm your email before logging in.
2. Upload a UTF-8 `.md` or `.txt` document (up to 5 MB).
3. The backend splits its bytes in memory, embeds chunks with `BAAI/bge-small-en-v1.5`, and writes 384-dimensional vectors to Pinecone under the verified Supabase user ID.
4. Questions search only that same user's namespace. Retrieved text goes to Gemini, and the frontend displays the answer and source excerpts.

Original uploads are not saved locally. There is no file-list endpoint or document inventory. Pinecone can take a few seconds to make new vectors searchable.

## Local setup

Create a root `.env` containing:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
PINECONE_API_KEY=your-pinecone-key
GEMINI_API_KEY=your-gemini-key
PINECONE_INDEX=rag-poc
GEMINI_MODEL=gemini-3.8-flash
```

Use a Gemini model ID available to your project. Keep these credentials on the backend. The existing Pinecone index must have 384 dimensions; a missing index is created in AWS `us-east-1` using cosine similarity.

From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev
```

The root `pyproject.toml` points to `src.api:app`. You can also run `uvicorn src.api:app --reload`. The embedding model is loaded on the first upload or question and cached for the process.

In another terminal:

```sh
cd Frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Optionally set `VITE_API_URL` in `Frontend/.env` to change the default backend URL (`http://127.0.0.1:8000`).

For Docker, run `docker compose up --build` from the repository root. Compose passes the Supabase, Pinecone, and Gemini environment variables to the backend. No local document/vector volumes are needed.

## API

| Route | Authentication | Purpose |
| --- | --- | --- |
| `POST /signup` | None | `{name, email, password}` → session or email-confirmation notice |
| `POST /login` | None | `{email, password}` → session |
| `POST /upload` | Bearer token | Multipart `file` → indexed filename and chunk count |
| `POST /chat` | Bearer token | `{message}` → `{answer, sources}` |

Both auth routes use the same response shape: `requires_confirmation`, plus either `message` or `user`, `access_token`, and `expires_at`. The UI keeps the session in tab-scoped session storage, clears it on sign out, and asks users to log in again after expiration. Passwords are never stored in browser storage. Sign out clears the local session; token refresh and server-side session revocation are not implemented.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests
cd Frontend
npm test
npm run build
```

Regression tests mock cloud services and the embedding model. They check auth contracts, token validation, upload validation, namespace routing, chunk metadata, and source responses without creating accounts or modifying live cloud data.

## Current limitations

- Only Markdown and plain text are supported; PDF extraction is not implemented.
- Chat history is held in memory and clears on refresh or sign out.
- Reuploading the same filename replaces its chunks and removes trailing chunks after successful writes. Pinecone updates are eventually consistent and are not atomic across batches; distributed concurrent uploads and document versioning are not implemented.
- This is a proof of concept, not a production authentication or document-management platform.
