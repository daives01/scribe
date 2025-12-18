from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NoteBase(BaseModel):
    title: Optional[str] = None
    content: str
    tags: List[str] = []
    note_type: str = "Quick Thought"
    metadata: dict = {}

class NoteCreate(NoteBase):
    pass

class Note(NoteBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    id: int
    title: Optional[str] = None
    content: str
    tags: List[str]
    note_type: str
    metadata: dict
    score: float
    created_at: Optional[str] = None

