"""Object-storage adapter factory. Selects based on env config."""

from __future__ import annotations

from functools import lru_cache

from app.adapters.storage.protocol import ObjectStorage, UploadedObject
from app.adapters.storage.s3 import S3Storage
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    return S3Storage(get_settings())


__all__ = ["ObjectStorage", "UploadedObject", "get_storage"]
