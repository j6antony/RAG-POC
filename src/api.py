from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
from supabase import create_client, Client
import os

from rag import answer_request
from services import get_embedder, get_vectorDB
from authentification import get_user_access


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

def get_current_user(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")

    try:
        response = supabase.auth.get_user(token)
        return response.user

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
app = FastAPI()
#the middleware was required becuase the react front end exists in a different port so without this the communication would get blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# for scalability is better to implement the type with the BaseModel thing\
#this is the backend response when a request is send by the user
class Auth(BaseModel):
    email:str
    password:str

class info(BaseModel):
    name: str
    email: str
    password: str
    role: str
class HistoryMessage(BaseModel):
    role: str
    text: str
class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage]
    conversation_id: UUID
@app.post("/chat")
async def chat(request: ChatRequest, autherization: str = Header(...)):
    user = get_current_user(autherization)
    user_access = get_user_access(supabase, user.id)

    if user_access not in [1, 2, 3]:
        raise HTTPException(status_code=403, detail="User has no valid access level")

    answer = await answer_request(
        request.message,
        request.history,
        user.id,
        user.user_metadata,
        str(request.conversation_id),
        user_access
    )

    return {
        "answer": answer
    }

#response on backend when a file is uploaded
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), autherization: str = Header(...), access_level: int = Form(...)):
    user = get_current_user(autherization)
    user_access = get_user_access(supabase, user.id)
    if user_access not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid Access Level")
    if access_level not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid Access Level")
    if access_level > user_access:
        raise HTTPException(
            status_code=403,
            detail="You cannot assign a higher access level"
        )
    contents = await file.read()
    #call the function to re-emebed the database
    embedder = get_embedder()
    vectorDB = get_vectorDB()
    embedder.embed(file.filename, contents, user.id, vectorDB, access_level)
    return {
        "message": "file uploaded successfully",
        "filename": file.filename
    }
@app.post("/login")
def login(input: Auth):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": input.email,
            "password": input.password
        })
        if response.session is None:
            return {
                "requires_confirmation": True,
                "message": "Check your email to confirm your account, then log in.",
            }

        return {
            "requires_confirmation": False,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "name": (response.user.user_metadata or {}).get("name")
                        or response.user.email.split("@")[0],
        },
        "access_token": response.session.access_token,
        }
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="invalid password or email"
        )
@app.post("/signup")
def signup(input: info):

    response = supabase.auth.sign_up({
        "email": input.email,
        "password": input.password,
        "options": {
            "data": {
                "name": input.name
            }
        }
    })
    supabase.table("user_roles").insert({
        "user_id": response.user.id,
        "role": input.role
    }).execute()
    if response.session is None:
        return {
            "requires_confirmation": True,
            "message": "Check your email to confirm your account."
        }

    return {
    "requires_confirmation": False,
    "user": {
        "id": response.user.id,
        "email": response.user.email,
        "name": (response.user.user_metadata or {}).get("name")
    },
    "access_token": response.session.access_token
    }




