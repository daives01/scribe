from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def generate_embeddings(self, text: str):
        """
        Generates a vector embedding for the given text.
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def generate_batch_embeddings(self, texts: list[str]):
        """
        Generates embeddings for a list of texts.
        """
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

# Global instance
embedding_service = EmbeddingService()
