"""Embedding wrapper using SentenceTransformer for LangChain."""
import logging
from functools import lru_cache
from typing import List
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_sentence_transformer_model():
    """Lazily loads and caches the SentenceTransformer model."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)


class CivicPulseEmbeddings(Embeddings):
    """LangChain Embeddings implementation wrapping SentenceTransformer."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name

    @property
    def model(self):
        return get_sentence_transformer_model()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute doc embeddings using SentenceTransformer."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Compute query embedding using SentenceTransformer."""
        if not text:
            text = " "
        embedding = self.model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()
