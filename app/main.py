import os
import uuid
import json
import sqlite3
import struct
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional

from app.database import get_db_connection, init_db
from app.models import Note, SearchResult
from app.services.transcriber import transcriber
from app.services.embeddings import embedding_service
from app.services.llm import llm_service
from app.services.search import search_service
from app.services.notifier import notifier

app = FastAPI(title="Scribe")

# Setup directories
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Fetch recent notes
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT 10")
    rows = cursor.fetchall()
    notes = []
    for row in rows:
        notes.append({
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"]
        })
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "notes": notes})

async def cleanup_temp_file(file_path: str):
    """
    Deletes the temporary audio file after processing.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {e}")

@app.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # Save temporary file
    file_ext = file.filename.split(".")[-1]
    file_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_DIR, f"{file_id}.{file_ext}")
    
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        # 1. Transcribe
        transcription = transcriber.transcribe(temp_path)
        content = transcription["text"]

        print(f"Transcription: {content}")
        # 2. No AI summary/analysis for MVP
        summary = None
        tags = []
        
        # 3. Generate Embedding
        embedding = embedding_service.generate_embeddings(content)
        
        # 4. Save to Database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notes (title, content, summary, tags, audio_path)
            VALUES (?, ?, ?, ?, ?)
        """, (None, content, summary, json.dumps(tags), temp_path))
        
        note_id = cursor.lastrowid
        
        # Save vector embedding
        embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)
        cursor.execute("""
            INSERT INTO vec_notes (id, embedding)
            VALUES (?, ?)
        """, (note_id, embedding_blob))
        
        conn.commit()
        conn.close()
        
        # 5. Notify & Cleanup
        background_tasks.add_task(
            notifier.notify, 
            "New Scribe Note", 
            f"Transcribed: {content[:100]}..."
        )
        background_tasks.add_task(cleanup_temp_file, temp_path)
        
        # Return a fragment for HTMX to swap
        return HTMLResponse(content=f"""
            <div class="p-4 bg-green-100 border border-green-400 text-green-700 rounded mb-4">
                Audio processed successfully!
            </div>
            <div hx-get="/notes/recent" hx-trigger="load" hx-target="#notes-list"></div>
        """)
        
    except Exception as e:
        # Cleanup file on error
        background_tasks.add_task(cleanup_temp_file, temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/recent")
async def get_recent_notes(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT 10")
    rows = cursor.fetchall()
    notes = []
    for row in rows:
        notes.append({
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "created_at": row["created_at"]
        })
    conn.close()
    return templates.TemplateResponse("fragments/note_list.html", {"request": request, "notes": notes})

@app.get("/search")
async def search_notes(request: Request, q: str):
    if not q:
        return HTMLResponse("")
    
    results = search_service.search(q)
    return templates.TemplateResponse("fragments/search_results.html", {"request": request, "results": results})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
