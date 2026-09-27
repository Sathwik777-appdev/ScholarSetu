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


from pathlib import Path


class LocalFileStore:
    def __init__(self, base_dir: str = "/tmp/scholarsetu_wallet"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        target = self.base_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    async def get(self, key: str) -> bytes:
        target = self.base_dir / key
        if not target.exists():
            raise StorageUnavailable(f"Document {key} not found")
        return target.read_bytes()


_store = None


def get_object_store():
    """FastAPI dependency; uses MinIO if credentials are configured, or local file store."""
    global _store
    if _store is not None:
        return _store

    if settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY:
        _store = ObjectStore(settings.MINIO_URL, settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY,
                             settings.MINIO_BUCKET)
    else:
        _store = LocalFileStore()
    return _store

