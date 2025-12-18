import json
import struct
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.models import Note, SearchResult

class NoteRepository:
    def get_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, tags, note_type, metadata, created_at 
                FROM notes 
                WHERE id = ?
            """, (note_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "note_type": row["note_type"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "created_at": row["created_at"]
            }

    def update(self, 
               note_id: int, 
               title: Optional[str] = None, 
               content: Optional[str] = None,
               tags: Optional[List[str]] = None,
               note_type: Optional[str] = None) -> bool:
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        if note_type is not None:
            updates.append("note_type = ?")
            params.append(note_type)
            
        if not updates:
            return False
            
        params.append(note_id)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE notes 
                SET {", ".join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, note_id: int) -> bool:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            cursor.execute("DELETE FROM vec_notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, tags, note_type, metadata, created_at 
                FROM notes 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            notes = []
            for row in rows:
                notes.append({
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "note_type": row["note_type"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"]
                })
            return notes

    def create(self, 
               title: str, 
               content: str, 
               tags: List[str], 
               note_type: str, 
               metadata: Dict[str, Any], 
               embedding: List[float]) -> int:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Insert into notes table
            cursor.execute("""
                INSERT INTO notes (title, content, tags, note_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (title, content, json.dumps(tags), note_type, json.dumps(metadata)))
            
            note_id = cursor.lastrowid
            
            # Save vector embedding
            embedding_blob = struct.pack(f"{len(embedding)}f", *embedding)
            cursor.execute("""
                INSERT INTO vec_notes (id, embedding)
                VALUES (?, ?)
            """, (note_id, embedding_blob))
            
            conn.commit()
            return note_id

    def search(self, query_embedding: List[float], limit: int = 5) -> List[SearchResult]:
        query_blob = struct.pack(f"{len(query_embedding)}f", *query_embedding)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    n.id, 
                    n.title, 
                    n.content,
                    n.tags, 
                    n.note_type,
                    n.metadata,
                    n.created_at,
                    v.distance
                FROM vec_notes v
                JOIN notes n ON n.id = v.id
                WHERE embedding MATCH ?
                AND k = ?
                ORDER BY distance
            """, (query_blob, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(SearchResult(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    note_type=row["note_type"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    score=1.0 / (1.0 + row["distance"]),
                    created_at=row["created_at"]
                ))
            return results

    def get_similar(self, note_id: int, limit: int = 5) -> List[SearchResult]:
        with get_db() as conn:
            cursor = conn.cursor()
            # 1. Get embedding for the source note
            cursor.execute("SELECT embedding FROM vec_notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            if not row:
                return []
            
            embedding_blob = row["embedding"]
            
            # 2. Search for similar notes excluding the source note
            cursor.execute("""
                SELECT 
                    n.id, 
                    n.title, 
                    n.content,
                    n.tags, 
                    n.note_type,
                    n.metadata,
                    n.created_at,
                    v.distance
                FROM vec_notes v
                JOIN notes n ON n.id = v.id
                WHERE embedding MATCH ?
                AND k = ?
                AND n.id != ?
                ORDER BY distance
            """, (embedding_blob, limit + 1, note_id))
            
            results = []
            for row in cursor.fetchall():
                results.append(SearchResult(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    note_type=row["note_type"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    score=1.0 / (1.0 + row["distance"]),
                    created_at=row["created_at"]
                ))
            return results[:limit]

note_repository = NoteRepository()
