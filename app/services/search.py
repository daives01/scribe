import json
from app.database import get_db_connection
from app.services.embeddings import embedding_service
from app.models import SearchResult

class SearchService:
    def search(self, query: str, limit: int = 5):
        """
        Performs a vector search for the given query.
        """
        query_embedding = embedding_service.generate_embeddings(query)
        # Convert list of floats to binary for sqlite-vec
        # Actually sqlite-vec handles list of floats in some versions or we use serialize_float32
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Using the k-nearest neighbors search in sqlite-vec
        # The syntax for vec0 is:
        # SELECT id, distance FROM vec_notes WHERE embedding MATCH ? ORDER BY distance LIMIT ?
        
        # We need to pass the embedding as a blob or a special format.
        # sqlite_vec provides helpers if needed, but standard blob works if format is correct.
        
        # Let's use the simplest approach for sqlite-vec v0.1.x
        import struct
        query_blob = struct.pack(f"{len(query_embedding)}f", *query_embedding)

        cursor.execute("""
            SELECT 
                n.id, 
                n.title, 
                n.content,
                n.summary, 
                n.tags, 
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
                summary=row["summary"] or "",
                tags=json.loads(row["tags"]) if row["tags"] else [],
                score=1.0 / (1.0 + row["distance"]) # Simple conversion from distance to score
            ))
            
        conn.close()
        return results

search_service = SearchService()

