from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import shutil

from rag import answer_request


Root_Dir = Path(__file__).resolve().parent.parent
Data_Dir = Root_Dir / "Raw Data"

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
    file_path = Data_Dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)# the shutil thing is straight from chat
    return {
        "message": "file uploaded successfully",
        "filename": file.filename
    }

#response on backend to show the front end what files are in the knowledge base
@app.post("/files")
def files():
    files = []
    for file in Data_Dir.iterdir():
        if file.is_file():
            files.append(file.name)
    return{
        "files": files
    }



