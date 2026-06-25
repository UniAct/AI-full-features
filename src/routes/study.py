"""
Study Area routes module for handling separate document uploads and notes.
Uses a JSON-based database to keep the Study Area completely decoupled from the main RAG system.
"""

from fastapi import APIRouter, UploadFile, status, Request
from fastapi.responses import JSONResponse, FileResponse
import os
import aiofiles
import json
import uuid
import logging
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger("uvicorn.error")

study_router = APIRouter(
    prefix="/api/v1/study",
    tags=["api_v1", "study"],
)

# Persistent volume directory for study files (must be inside /assets/files which is mounted)
STUDY_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../assets/files/study"))

def get_project_db_path(project_id: str) -> str:
    return os.path.join(STUDY_DIR, f"study_db_{project_id}.json")

def ensure_study_dir():
    if not os.path.exists(STUDY_DIR):
        os.makedirs(STUDY_DIR, exist_ok=True)

class BookmarkInput(BaseModel):
    label: str
    page: int

class StudyDataInput(BaseModel):
    notes: str
    bookmarks: List[BookmarkInput]

async def read_db(project_id: str) -> dict:
    ensure_study_dir()
    db_path = get_project_db_path(project_id)
    if not os.path.exists(db_path):
        return {"files": [], "data": {}}
    try:
        async with aiofiles.open(db_path, "r") as f:
            content = await f.read()
            return json.loads(content)
    except Exception:
        return {"files": [], "data": {}}

async def write_db(project_id: str, db: dict):
    ensure_study_dir()
    db_path = get_project_db_path(project_id)
    try:
        async with aiofiles.open(db_path, "w") as f:
            await f.write(json.dumps(db))
    except Exception as e:
        logger.error(f"Failed to write study DB: {e}")

@study_router.post("/upload/{project_id}")
async def upload_study_file(project_id: str, file: UploadFile):
    """Uploads a PDF exclusively to the Study Area."""
    ensure_study_dir()
    
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files are allowed"})
        
    file_id = str(uuid.uuid4())
    filename = file.filename
    file_path = os.path.join(STUDY_DIR, f"{file_id}.pdf")
    
    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                
        file_size = os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"Failed to save study file: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to save file"})
        
    db = await read_db(project_id)
    
    # Store file metadata
    file_entry = {
        "id": file_id,
        "name": filename,
        "size": file_size
    }
    db["files"].append(file_entry)
    
    # Initialize empty data for this file
    db["data"][file_id] = {
        "notes": "",
        "bookmarks": []
    }
    
    await write_db(project_id, db)
    
    return JSONResponse(content={"signal": "File uploaded", "file": file_entry})

@study_router.get("/files/{project_id}")
async def list_study_files(project_id: str):
    """Lists all files uploaded to the Study Area."""
    db = await read_db(project_id)
    return JSONResponse(content={"files": db["files"]})

@study_router.get("/serve/{project_id}/{file_id}")
async def serve_study_file(project_id: str, file_id: str):
    """Serves the raw PDF for viewing."""
    file_path = os.path.join(STUDY_DIR, f"{file_id}.pdf")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
        
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"}
    )

@study_router.post("/data/{project_id}/{file_id}")
async def save_study_data(project_id: str, file_id: str, data: StudyDataInput):
    """Saves notes and bookmarks for a specific file."""
    db = await read_db(project_id)
    
    if file_id not in [f["id"] for f in db["files"]]:
        return JSONResponse(status_code=404, content={"error": "File not found in study DB"})
        
    db["data"][file_id] = {
        "notes": data.notes,
        "bookmarks": [bm.model_dump() for bm in data.bookmarks]
    }
    
    await write_db(project_id, db)
    return JSONResponse(content={"signal": "Data saved successfully"})

@study_router.get("/data/{project_id}/{file_id}")
async def get_study_data(project_id: str, file_id: str):
    """Retrieves notes and bookmarks for a specific file."""
    db = await read_db(project_id)
    
    if file_id not in db["data"]:
        return JSONResponse(content={"notes": "", "bookmarks": []})
        
    return JSONResponse(content=db["data"][file_id])
