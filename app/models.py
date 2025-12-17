from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NoteBase(BaseModel):
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    tags: List[str] = []

class NoteCreate(NoteBase):
    pass

class Note(NoteBase):
    id: int
    created_at: datetime
    audio_path: Optional[str] = None

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    tags: List[str]
    score: float

