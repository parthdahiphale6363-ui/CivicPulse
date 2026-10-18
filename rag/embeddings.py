"""Embedding wrapper using FastEmbed (ONNX, no torch)."""
import os
import logging
from functools import lru_cache
from typing import List, Tuple

# Ensure single-threaded execution for ONNX / OpenMP
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = MODEL_NAME):
    """Lazily loads and caches the FastEmbed TextEmbedding model (ONNX runtime, threads=1, no PyTorch)."""
    from fastembed import TextEmbedding
    logger.info(f"Loading FastEmbed model: {model_name} (threads=1)")
    return TextEmbedding(model_name=model_name, threads=1)


# Retain alias for backward compatibility
def get_sentence_transformer_model():
    return get_embedding_model()


@lru_cache(maxsize=256)
def embed_query_cached(text: str, model_name: str = MODEL_NAME) -> Tuple[float, ...]:
    """Compute and cache query embedding as an immutable tuple of floats with LRU cache (256)."""
    clean_text = text.strip() if text and text.strip() else " "
    model = get_embedding_model(model_name)
    emb = list(model.query_embed(clean_text))[0]
    return tuple(float(x) for x in emb)


def embed_documents_list(texts: List[str], model_name: str = MODEL_NAME) -> List[List[float]]:
    """Compute doc embeddings using FastEmbed."""
    if not texts:
        return []
    model = get_embedding_model(model_name)
    embeddings = list(model.embed(texts))
    return [emb.tolist() for emb in embeddings]


class CivicPulseEmbeddings:
    """LangChain-compatible Embeddings implementation wrapping FastEmbed TextEmbedding."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name

    @property
    def model(self):
        return get_embedding_model(self.model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute doc embeddings using FastEmbed."""
        return embed_documents_list(texts, self.model_name)

    def embed_query(self, text: str) -> List[float]:
        """Compute query embedding using FastEmbed (with LRU cache 256)."""
        return list(embed_query_cached(text, self.model_name))


def is_embedding_model_loaded() -> bool:
    """Check if the FastEmbed embedding model is currently in memory."""
    try:
        return get_embedding_model.cache_info().currsize > 0
    except Exception:
        return False



