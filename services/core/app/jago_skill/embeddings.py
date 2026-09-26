"""Sentence embeddings for guideline search (ONNX via fastembed; no GPU or PyTorch needed)."""

import asyncio
import threading
from typing import Optional

from app.config import settings


class Embedder:
    def __init__(self, model_name: str, cache_dir: Optional[str] = None):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(self.model_name, cache_dir=self.cache_dir)
        return self._model

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._load().embed(texts)]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_sync, texts)


_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_CACHE_DIR)
    return _embedder
