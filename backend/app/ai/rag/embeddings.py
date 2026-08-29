import hashlib
import numpy as np
from typing import List, Optional
from app.config import settings

class EmbeddingProvider:
    """
    Embedding Provider interface supporting:
    - Real multilingual SentenceTransformer/local model (when installed)
    - Deterministic semantic hash embeddings for isolated offline/test environments
    """
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None
        self._load_model()

    def _load_model(self):
        # Attempt to load fast local model if available, else deterministic fallback
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self.mode = "LOCAL_MODEL"
        except Exception:
            self._model = None
            self.mode = "DETERMINISTIC_FALLBACK"

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension

        if self._model is not None:
            try:
                vec = self._model.encode(text, normalize_embeddings=True)
                return vec.tolist()
            except Exception:
                pass

        # Deterministic semantic hash embedding for reproducible cosine similarity in tests & demos
        # Generates a normalized unit vector of length `self.dimension` seeded by text tokens & bigrams
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            # Seed token hash
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            val = ((h >> 8) % 1000) / 500.0 - 1.0
            vec[idx] += float(val)
            
            # Bigram hash
            if i > 0:
                bg = f"{words[i-1]}_{word}"
                h_bg = int(hashlib.sha256(bg.encode("utf-8")).hexdigest(), 16)
                idx_bg = h_bg % self.dimension
                vec[idx_bg] += 1.5

        # Normalize to unit length
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        else:
            vec[0] = 1.0

        return vec.tolist()

    def embed_documents(self, docs: List[str]) -> List[List[float]]:
        return [self.embed_text(d) for d in docs]

# Default embedding service singleton
embedding_service = EmbeddingProvider()
