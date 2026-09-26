"""Object storage for wallet documents (MinIO / any S3-compatible store)."""

import asyncio
import io
from typing import Optional
from urllib.parse import urlparse

from app.config import settings


class StorageUnavailable(Exception):
    pass


class ObjectStore:
    def __init__(self, url: str, access_key: str, secret_key: str, bucket: str):
        from minio import Minio
        parsed = urlparse(url)
        self._client = Minio(parsed.netloc, access_key=access_key, secret_key=secret_key,
                             secure=parsed.scheme == "https")
        self.bucket = bucket
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if not self._bucket_ready:
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
            self._bucket_ready = True

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        def _put():
            self._ensure_bucket()
            self._client.put_object(self.bucket, key, io.BytesIO(data), len(data), content_type=content_type)
        try:
            await asyncio.to_thread(_put)
        except Exception as exc:
            raise StorageUnavailable(str(exc)) from exc

    async def get(self, key: str) -> bytes:
        def _get():
            response = self._client.get_object(self.bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        try:
            return await asyncio.to_thread(_get)
        except Exception as exc:
            raise StorageUnavailable(str(exc)) from exc


_store: Optional[ObjectStore] = None


def get_object_store() -> ObjectStore:
    """FastAPI dependency; tests override it with an in-memory store."""
    global _store
    if not (settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Object storage is not configured (MINIO_ACCESS_KEY / MINIO_SECRET_KEY)")
    if _store is None:
        _store = ObjectStore(settings.MINIO_URL, settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY,
                             settings.MINIO_BUCKET)
    return _store
