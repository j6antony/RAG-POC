"""HTTP API for Supabase authentication and user-scoped Pinecone documents."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import ClientOptions, create_client
from supabase_auth.errors import AuthApiError

from src.embedding import get_embedder
from src.rag import answer_request

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
logger = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_methods=['POST'],
    allow_headers=['Content-Type', 'Authorization'],
)


def get_supabase():
    url, key = os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise HTTPException(503, 'Supabase is not configured.')
    # Each request has its own client: never share a signed-in user's session.
    return create_client(url, key, options=ClientOptions(
        persist_session=False, auto_refresh_token=False,
    ))


def get_current_user(authorization: str | None = Header(default=None), client=Depends(get_supabase)):
    scheme, _, token = (authorization or '').partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(401, 'Please log in to continue.', headers={'WWW-Authenticate': 'Bearer'})
    try:
        response = client.auth.get_user(token.strip())
    except AuthApiError as error:
        raise HTTPException(401, 'Invalid or expired token.', headers={'WWW-Authenticate': 'Bearer'}) from error
    except Exception as error:
        logger.exception('Unable to verify session')
        raise HTTPException(503, 'Authentication is temporarily unavailable.') from error
    if response is None or response.user is None:
        raise HTTPException(401, 'Invalid or expired token.')
    return response.user


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class SignupRequest(AuthRequest):
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8)


def auth_response(response):
    if response.session is None:
        return {'requires_confirmation': True, 'message': 'Check your email to confirm your account, then log in.'}
    if response.user is None:
        raise HTTPException(502, 'Authentication returned an incomplete session.')
    user = response.user
    return {
        'requires_confirmation': False,
        'user': {'id': user.id, 'email': user.email,
                 'name': (user.user_metadata or {}).get('name') or user.email.split('@')[0]},
        'access_token': response.session.access_token,
        'expires_at': response.session.expires_at,
    }


@app.post('/login')
def login(body: AuthRequest, client=Depends(get_supabase)):
    try:
        response = client.auth.sign_in_with_password({'email': str(body.email), 'password': body.password})
    except AuthApiError as error:
        raise HTTPException(401, 'Unable to log in. Check your email, password, and email confirmation.') from error
    except Exception as error:
        logger.exception('Login service failed')
        raise HTTPException(503, 'Login is temporarily unavailable. Please try again.') from error
    return auth_response(response)


@app.post('/signup')
def signup(body: SignupRequest, client=Depends(get_supabase)):
    if not body.name.strip():
        raise HTTPException(422, 'Please enter your name.')
    try:
        response = client.auth.sign_up({
            'email': str(body.email), 'password': body.password,
            'options': {'data': {'name': body.name.strip()}},
        })
    except AuthApiError as error:
        raise HTTPException(400, 'Unable to create account. Check your details or try logging in.') from error
    except Exception as error:
        logger.exception('Signup service failed')
        raise HTTPException(503, 'Signup is temporarily unavailable. Please try again.') from error
    return auth_response(response)


@app.post('/chat')
def chat(body: ChatRequest, user=Depends(get_current_user)):
    question = body.message.strip()
    if not question:
        raise HTTPException(422, 'Please enter a question.')
    try:
        return answer_request(question, user.id)
    except Exception as error:
        logger.exception('Chat failed')
        raise HTTPException(502, 'Could not generate an answer. Please try again.') from error


@app.post('/upload')
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    try:
        filename = Path((file.filename or '').replace('\\', '/')).name
        if Path(filename).suffix.lower() not in {'.md', '.txt'}:
            raise HTTPException(415, 'Upload a UTF-8 Markdown (.md) or text (.txt) file.')
        contents = await file.read(5 * 1024 * 1024 + 1)
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(413, 'Files must be 5 MB or smaller.')
        try:
            if not contents.decode('utf-8').strip():
                raise HTTPException(422, 'The document is empty.')
        except UnicodeDecodeError as error:
            raise HTTPException(415, 'The document must contain UTF-8 text.') from error
        try:
            def index_document():
                return get_embedder().embed(filename, contents, user.id)
            count = await run_in_threadpool(index_document)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            logger.exception('Document indexing failed')
            raise HTTPException(502, 'Could not index the document. Please try again.') from error
        return {'message': 'Document indexed successfully.', 'filename': filename, 'chunks': count}
    finally:
        await file.close()
