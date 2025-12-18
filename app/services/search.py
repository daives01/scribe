from typing import List
from app.services.embeddings import embedding_service
from app.repositories.note_repository import note_repository
from app.models import SearchResult

class SearchService:
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Performs a vector search for the given query.
        """
        if not query:
            return []
            
        query_embedding = embedding_service.generate_embeddings(query)
        return note_repository.search(query_embedding, limit)

    def get_similar_notes(self, note_id: int, limit: int = 4) -> List[SearchResult]:
        """
        Finds notes similar to the given note ID.
        """
        return note_repository.get_similar(note_id, limit)

search_service = SearchService()
