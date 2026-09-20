from fastapi import FastAPI, UploadFile, File
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import shutil

from embedding import Embed
from rag import answer_request
from storage import DATA_DIR



def clear_raw_data():

    DATA_DIR.mkdir(exist_ok=True)

    for path in DATA_DIR.iterdir():

        if path.is_file():
            path.unlink()

        elif path.is_dir():
            shutil.rmtree(path)
@asynccontextmanager
async def lifespan(app: FastAPI):

    # App starts
    yield

    # App shuts down
    clear_raw_data()

app = FastAPI(lifespan=lifespan)
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
class ChatRequest(BaseModel):
    message:str

@app.post("/chat")
def chat(request: ChatRequest):
    answer = answer_request(request.message)

    return {
        "answer": answer
    }

#response on backend when a file is uploaded
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = DATA_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)# the shutil thing is straight from chat
    #call the function to re-emebed the database
    embedder = Embed()
    embedder.embed_data_file(file_path)
    return {
        "message": "file uploaded successfully",
        "filename": file.filename
    }

#response on backend to show the front end what files are in the knowledge base
@app.get("/files")
def files():
    files = []
    for file in DATA_DIR.iterdir():
        if file.is_file():
            files.append(file.name)
    return{
        "files": files
    }



