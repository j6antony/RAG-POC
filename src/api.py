from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
from supabase import create_client, Client
import os
import logging
import json
import asyncio
from pathlib import Path
from typing import Literal
from fastapi.responses import Response
from document_images import extract_pdf, store_images, can_view_document, BUCKET

#from rag import answer_request
from guardrail_audit import begin_audit, end_audit, persist_hits, record_event
from guardrails import inspect_input
from controller import run_agent
from services import get_embedder, get_vectorDB
from authentification import get_user_access
from fastapi.responses import StreamingResponse

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
        "http://127.0.0.1:5173",
        "https://rag-poc-chi.vercel.app"
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
    #history: list[HistoryMessage] removing react passing chat history
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

    progress_queue = asyncio.Queue()

    async def progress(event):
        await progress_queue.put(event)
    async def run():
        token, events = begin_audit(user, request.conversation_id, user_access)
        try:
            record_event(event_type="request_started", source="chat")
            await inspect_input(request.message)
            return await run_agent(
                    request=request.message,
                    user_id=user.id,
                    username=username,
                    conversation_id=request.conversation_id,
                    user_access=user_access,
                    supabase=supabase,
                    progress=progress,
            )
        except Exception as error:
            record_event(event_type="request_failed", status="failed", source="chat",
                         details={"error_type": type(error).__name__})
            raise
        finally:
            end_audit(token)
            await asyncio.to_thread(persist_hits, supabase, events)
    def format_sse(event_type, data):
        payload = json.dumps(data)

        return (
            f"event: {event_type}\n"
            f"data: {payload}\n\n"
        )
    async def event_stream():
        task = asyncio.create_task(run())

        try:
            while not task.done():

                try:
                    event = await asyncio.wait_for(
                        progress_queue.get(),
                        timeout=0.25,
                    )

                    yield format_sse(
                        "progress",
                        event
                    )

                except asyncio.TimeoutError:
                    continue

            result = await task

            # Drain anything emitted immediately
            # before the task completed.
            while not progress_queue.empty():
                event = progress_queue.get_nowait()

                yield format_sse(
                    "progress",
                    event
                )

            yield format_sse(
                "complete",
                result
            )

        except Exception as exc:

            yield format_sse(
                "error",
                {
                    "message": str(exc)
                }
            )
        

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )




#response on backend when a file is uploaded
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), autherization: str = Header(...), access_level: int = Form(...), classification: str = Form("internal"), contains_sensitive_data: bool = Form(False)):
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
    CLASSIFICATIONS = {
        "public",
        "internal",
        "confidential",
        "restricted"
    }

    CLASSIFICATIONS_LEVELS = {
        "public": 1,
        "internal": 1,
        "confidential": 2,
        "restricted": 3
    }

    classification = classification.lower().strip()
    if classification not in CLASSIFICATIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid document classification"
        )

    required_level = CLASSIFICATIONS_LEVELS[classification]
    if access_level < required_level:
        raise HTTPException(
            status_code=400,
            detail=f"{classification.title()} documents require access level of {required_level} or higher"
        )

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
            "visibility": visibility,
            "classification": classification,
            "contains_sensitive_data": contains_sensitive_data
        }).execute()
    )
    document_id = response.data[0]["id"]
    paths = []
    try:
        if images:
            paths = store_images(supabase, document_id, images)
        if chunks is None:
            embedder.embed(file.filename, contents, user.id, vectorDB, access_level, document_id, classification, contains_sensitive_data)
        else:
            embedder.embed(file.filename, contents, user.id, vectorDB, access_level, document_id,classification, contains_sensitive_data, chunks=chunks)
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
            "classification": classification,
            "contains_sensitive_data": contains_sensitive_data,
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
        .select("id,filename,uploaded_by,visibility,classification,contains_sensitive_data,created_at")
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

@app.get("/conversations")
def get_conversations(autherization: str = Header(...)):
    user = get_current_user(authorization=autherization)
    result = (
        supabase.table("conversations").select("id", "name", "created_at").eq("user_id", str(user.id)).order("created_at", desc=True).execute()
    )
    return {
        "conversations": result.data or []
    }

@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id, autherization: str = Header(...)):
    user = get_current_user(autherization)
    #check if the conversation exists first
    conversation = supabase.table("conversations").select("id").eq("id", str(conversation_id)).eq("user_id", str(user.id)).limit(1).execute()
    if not conversation.data:
        raise HTTPException(status_code=404, detail="No conversation found")
    # retain all the messages from the given conversation
    messages = (
        supabase
        .table("conversation_messages")
        .select("id", "role", "text", "created_at")
        .eq("conversation_id", str(conversation_id))
        .eq("user_id", str(user.id))
        .order("created_at", desc=False) 
        .execute()
    )
    return {
        "messages": messages.data or []
    }

@app.get("/me/access")
def current_access(autherization: str = Header(...)):
    user = get_current_user(autherization)
    return {"access_level": get_user_access(supabase, user.id)}


@app.get("/admin/audit-events")
def audit_events(
    autherization: str = Header(...),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    event_type: Literal["request_started", "request_failed", "model_called", "tool_called", "document_retrieved", "guardrail", "response_generated"] | None = None,
    status: Literal["started", "success", "failed", "flagged", "blocked"] | None = None,
):
    user = get_current_user(autherization)
    if get_user_access(supabase, user.id) != 3:
        raise HTTPException(status_code=403, detail="Admin access is required.")
    try:
        query = supabase.table("ai_audit_events").select("*")
        if event_type:
            query = query.eq("event_type", event_type)
        if status:
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).order("id", desc=True).range(offset, offset + limit).execute()
    except Exception:
        logging.getLogger(__name__).error("AI audit history unavailable; check migration and database access.")
        raise HTTPException(status_code=503, detail="AI audit history is unavailable. Check that the AI audit events table has been applied.")
    rows = result.data or []
    return {"events": rows[:limit], "has_more": len(rows) > limit}
