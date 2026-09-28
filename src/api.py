from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
from supabase import create_client, Client
import os

from rag import answer_request
from services import get_embedder, get_vectorDB
from autherization import Autherization


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

    authz = Autherization(supabase)

    roles = authz.get_roles(user.id)
    department = authz.get_department(user.id)

    if not roles:
        raise HTTPException(
            status_code=403,
            detail="User has no assigned role"
        )

    # For your current setup, assume one role per user
    role = roles[0]

    answer = await answer_request(
        request.message,
        request.history,
        user.id,
        user.user_metadata,
        str(request.conversation_id),
        role,
        department
    )

    return {
        "answer": answer
    }

#response on backend when a file is uploaded
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), visibility = Form(...), autherization: str = Header(...)):
    user = get_current_user(autherization)
    contents = await file.read()
    authz = Autherization(supabase)

    roles = authz.get_roles(user.id)
    department = authz.get_department(user.id)
    if "manager" in roles:
        visibility = "company"
    else:
        visibility = "department"

    #call the function to re-emebed the database
    embedder = get_embedder()
    vectorDB = get_vectorDB()
    embedder.embed(file.filename, contents, user.id, vectorDB, visibility, department)
    return {
        "message": "file uploaded successfully",
        "filename": file.filename, 
        "visibility": visibility
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




