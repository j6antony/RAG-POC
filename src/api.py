from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
from supabase import create_client, Client
import os
import logging
from pathlib import Path
from typing import Literal
from fastapi.responses import Response
from document_images import extract_pdf, store_images, can_view_document, BUCKET

#from rag import answer_request
from controller import run_agent
from services import get_embedder, get_vectorDB
from authentification import get_user_access

VISIBILITY_LEVELS = {"user": 1, "manager": 2, "admin": 3}


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Keep this database client free of user sessions. Login/signup use separate clients.
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

def get_current_user(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")

    try:
        response = supabase.auth.get_user(token)
        if response.user is None:
            raise ValueError("Missing user")
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
    role: Literal["user", "manager", "admin"]
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

    username = (
        (user.user_metadata or {}).get("name")
        or user.email.split("@")[0]
    )

    answer = await run_agent(
        request=request.message,
        history=request.history,
        user_id=user.id,
        username=username,
        conversation_id=request.conversation_id,
        user_access=user_access,
        supabase=supabase
    )

    return answer if isinstance(answer, dict) else {"answer": answer, "images": []}

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
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".md", ".txt", ".pdf"}:
        raise HTTPException(status_code=400, detail="Upload a PDF, Markdown, or text file.")
    contents = await file.read(20 * 1024 * 1024 + 1)
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Files must be 20 MB or smaller.")
    chunks, images = None, []
    try:
        if extension == ".pdf":
            chunks, images = extract_pdf(contents, file.filename)
        elif not contents.decode("utf-8").strip():
            raise ValueError("The file is empty.")
    except (ValueError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    if access_level == 1:
        visibility = "user"
    elif access_level == 2:
        visibility = "manager"
    else:
        visibility = "admin"
    embedder = get_embedder()
    vectorDB = get_vectorDB()
    response = (
        supabase
        .table("knowledge_documents")
        .insert({
            "filename": file.filename,
            "uploaded_by": str(user.id),
            "visibility": visibility
        }).execute()
    )
    document_id = response.data[0]["id"]
    paths = []
    try:
        if images:
            paths = store_images(supabase, document_id, images)
        if chunks is None:
            embedder.embed(file.filename, contents, user.id, vectorDB, access_level, document_id)
        else:
            embedder.embed(file.filename, contents, user.id, vectorDB, access_level, document_id, chunks=chunks)
    except Exception as error:
        logging.exception("Document indexing failed for %s", document_id)
        # Remove vectors first so a failed upload cannot remain searchable.
        vectorDB.index.delete(filter={"document_id": {"$eq": str(document_id)}}, namespace="company")
        if paths:
            supabase.storage.from_(BUCKET).remove(paths)
        supabase.table("knowledge_documents").delete().eq("id", document_id).execute()
        raise HTTPException(status_code=500, detail="Document indexing failed. Check image storage setup and backend logs.") from error
    return {
            "message": "file uploaded successfully",
            "document_id": document_id,
            "filename": file.filename,
            "visibility": visibility,
            "image_count": len(images)
        }
@app.post("/login")
def login(input: Auth):
    try:
        response = create_client(SUPABASE_URL, SUPABASE_KEY).auth.sign_in_with_password({
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

    response = create_client(SUPABASE_URL, SUPABASE_KEY).auth.sign_up({
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
@app.get("/knowledge")
async def get_knowledge(
    autherization: str = Header(...)
):
    user = get_current_user(autherization)

    user_access = get_user_access(supabase, user.id)
    if user_access not in [1, 2, 3]:
        raise HTTPException(status_code=403, detail="User has no valid access level")

    # Match Pinecone: lower levels, plus own documents at the same level.
    # Keep the existing text visibility column; no schema migration is needed.
    allowed = [name for name, level in VISIBILITY_LEVELS.items() if level <= user_access]
    response = (
        supabase.table("knowledge_documents")
        .select("id,filename,uploaded_by,visibility,created_at")
        .in_("visibility", allowed)
        .order("created_at", desc=True)
        .execute()
    )
    documents = [
        {**document, "access_level": VISIBILITY_LEVELS[document["visibility"]]}
        for document in (response.data or [])
        if VISIBILITY_LEVELS[document["visibility"]] < user_access
        or str(document["uploaded_by"]) == str(user.id)
    ]
    return {"documents": documents, "access_level": user_access}


@app.get("/knowledge/images/{image_id}")
def get_knowledge_image(image_id: UUID, autherization: str = Header(...)):
    user = get_current_user(autherization)
    access = get_user_access(supabase, user.id)
    if access not in (1, 2, 3):
        raise HTTPException(status_code=403, detail="User has no valid access level")
    rows = supabase.table("knowledge_images").select("*").eq("id", str(image_id)).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Image not found")
    image = rows[0]
    documents = supabase.table("knowledge_documents").select("*").eq("id", image["document_id"]).execute().data
    if not documents or not can_view_document(documents[0], user.id, access):
        raise HTTPException(status_code=404, detail="Image not found")
    content = supabase.storage.from_(BUCKET).download(image["image_path"])
    return Response(content, media_type="image/png", headers={"Cache-Control": "private, no-store"})
