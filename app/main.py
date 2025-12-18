import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.repositories.note_repository import note_repository
from app.repositories.settings_repository import settings_repository
from app.services.transcriber import transcriber
from app.services.embeddings import embedding_service
from app.services.llm import llm_service
from app.services.search import search_service
from app.services.notifier import notifier

app = FastAPI(title="Scribe")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    notes = note_repository.get_recent(limit=10)
    return templates.TemplateResponse("index.html", {"request": request, "notes": notes})

async def cleanup_temp_file(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {e}")

async def process_audio_task(temp_path: str):
    """
    Background task to handle transcription, LLM processing, and database storage.
    """
    try:
        # 1. Transcribe
        transcription = transcriber.transcribe(temp_path)
        content = transcription["text"]

        # 2. LLM Analysis
        llm_result = await llm_service.summarize_and_tag(content)
        title = llm_result.get("title", "New Note")
        tags = llm_result.get("tags", [])
        note_type = llm_result.get("note_type", "Quick Thought")
        metadata = llm_result.get("metadata", {})
        
        # 3. Embeddings
        embedding = embedding_service.generate_embeddings(content)
        
        # 4. Save to DB
        note_id = note_repository.create(
            title=title,
            content=content,
            tags=tags,
            note_type=note_type,
            metadata=metadata,
            embedding=embedding
        )
        
        # 5. Notify
        await notifier.notify(
            "New Scribe Note", 
            f"[{note_type}] {title}: {content[:100]}..."
        )
        
        # 6. Cleanup
        await cleanup_temp_file(temp_path)
        print(f"Successfully processed note {note_id}: {title}")
        
    except Exception as e:
        print(f"Error processing audio task for {temp_path}: {e}")
        await cleanup_temp_file(temp_path)

@app.post("/upload")
async def upload_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    file_ext = file.filename.split(".")[-1]
    file_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_DIR, f"{file_id}.{file_ext}")
    
    # Save the file first
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Add processing to background tasks
    background_tasks.add_task(process_audio_task, temp_path)
    
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "fragments/upload_success.html", 
            {
                "request": request, 
                "title": "Your audio is being transcribed and analyzed.", 
                "note_type": "Processing"
            }
        )
    
    return JSONResponse(content={
        "status": "success",
        "message": "Upload received and processing started.",
        "siri_feedback": "Got it, I'm processing that note for you now."
    })

@app.get("/notes/recent")
async def get_recent_notes(request: Request):
    notes = note_repository.get_recent(limit=10)
    return templates.TemplateResponse("fragments/note_list.html", {"request": request, "notes": notes})

@app.get("/notes/{note_id}")
async def get_note_detail(request: Request, note_id: int):
    note = note_repository.get_by_id(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    similar_notes = search_service.get_similar_notes(note_id, limit=3)
    return templates.TemplateResponse(
        "fragments/note_detail.html", 
        {
            "request": request, 
            "note": note, 
            "similar_notes": similar_notes
        }
    )

@app.patch("/notes/{note_id}")
async def update_note(request: Request, note_id: int):
    form_data = await request.form()
    title = form_data.get("title")
    content = form_data.get("content")
    
    # We can add more fields if needed
    note_repository.update(note_id, title=title, content=content)
    
    note = note_repository.get_by_id(note_id)
    similar_notes = search_service.get_similar_notes(note_id, limit=3)
    return templates.TemplateResponse(
        "fragments/note_detail.html", 
        {
            "request": request, 
            "note": note, 
            "similar_notes": similar_notes,
            "success_message": "Note updated!"
        },
        headers={"HX-Trigger": "noteUpdated"}
    )

@app.delete("/notes/{note_id}")
async def delete_note(request: Request, note_id: int):
    note_repository.delete(note_id)
    if request.headers.get("HX-Request"):
        # If deleted from the detail view, we might want to show a message or redirect
        # For now, let's just return a success message or an empty response that triggers a reload of the list
        return HTMLResponse(content='<div class="p-8 text-center"><p class="text-slate-500">Note deleted.</p><button hx-get="/notes/recent" hx-target="#notes-list" class="mt-4 text-indigo-600 font-medium">Refresh list</button></div>', headers={"HX-Trigger": "noteDeleted"})
    return JSONResponse(content={"status": "success"})

@app.get("/search")
async def search_notes(request: Request, q: str):
    if not q:
        return HTMLResponse("")
    
    results = search_service.search(q)
    return templates.TemplateResponse("fragments/search_results.html", {"request": request, "results": results})

@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request, url: str = None, api_key: str = None):
    current_model = settings_repository.get("llm_model", "llama3")
    current_url = url or settings_repository.get("ollama_url", "http://localhost:11434")
    current_api_key = api_key if api_key is not None else settings_repository.get("ollama_api_key", "")
    
    # If a URL or API key was provided in the query, we use them to fetch models
    # This allows the UI to refresh the list when either is changed
    llm_info = await llm_service.get_available_models(url=current_url, api_key=current_api_key)
    available_models = llm_info["models"]
    connection_error = llm_info["error"]
    
    # Ensure current model is in the list even if not returned (e.g. if server is down)
    if current_model and current_model not in available_models:
        available_models.insert(0, current_model)
    
    return templates.TemplateResponse(
        "fragments/settings.html", 
        {
            "request": request, 
            "current_model": current_model,
            "current_url": current_url,
            "current_api_key": current_api_key,
            "available_models": available_models,
            "connection_error": connection_error
        }
    )

@app.post("/settings/llm")
async def update_llm_settings(request: Request):
    form_data = await request.form()
    model = form_data.get("model")
    url = form_data.get("url")
    api_key = form_data.get("api_key")
    
    if url:
        settings_repository.set("ollama_url", url)
    if model:
        settings_repository.set("llm_model", model)
    if api_key is not None:
        settings_repository.set("ollama_api_key", api_key)
    
    # Return the settings fragment again to show updated state
    current_model = settings_repository.get("llm_model", "llama3")
    current_url = settings_repository.get("ollama_url", "http://localhost:11434")
    current_api_key = settings_repository.get("ollama_api_key", "")
    
    llm_info = await llm_service.get_available_models()
    available_models = llm_info["models"]
    connection_error = llm_info["error"]
    
    if current_model and current_model not in available_models:
        available_models.insert(0, current_model)

    return templates.TemplateResponse(
        "fragments/settings.html", 
        {
            "request": request, 
            "current_model": current_model,
            "current_url": current_url,
            "current_api_key": current_api_key,
            "available_models": available_models,
            "connection_error": connection_error,
            "success_message": "Settings updated successfully!"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
