"""Object storage for wallet documents (MinIO / any S3-compatible store)."""

import asyncio
import io
from pathlib import Path
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



class LocalFileStore:
    """Development only (WALLET_LOCAL_DIR): documents on local disk. Not for production: a container's
    disk is lost on restart and is not shared between instances."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        target = (self.base_dir / key).resolve()
        if self.base_dir.resolve() not in target.parents:
            raise StorageUnavailable("invalid document key")
        return target

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        target = self._path(key)
        await asyncio.to_thread(lambda: (target.parent.mkdir(parents=True, exist_ok=True), target.write_bytes(data)))

    async def get(self, key: str) -> bytes:
        target = self._path(key)
        if not target.exists():
            raise StorageUnavailable(f"Document {key} not found")
        return await asyncio.to_thread(target.read_bytes)


_store = None


def get_object_store():
    """FastAPI dependency (tests override it with an in-memory store). Without object-store credentials the
    wallet reports 503, unless WALLET_LOCAL_DIR is set for development."""
    global _store
    if _store is not None:
        return _store
    if settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY:
        _store = ObjectStore(settings.MINIO_URL, settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY,
                             settings.MINIO_BUCKET)
    elif settings.WALLET_LOCAL_DIR:
        _store = LocalFileStore(settings.WALLET_LOCAL_DIR)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Document storage is not configured")
    return _store
