"""Object-storage protocol. Implementations live in sibling modules.

Single seam between application code and {MinIO, Supabase Storage, S3}.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class UploadedObject:
    object_key: str
    bytes_size: int
    mime_type: str


class ObjectStorage(Protocol):
    """Thin S3-shaped interface — works with boto3 against any S3-compatible store."""

    async def put_object(
        self,
        *,
        object_key: str,
        body: bytes,
        mime_type: str,
    ) -> UploadedObject: ...

    async def signed_get_url(self, object_key: str, *, ttl_seconds: int | None = None) -> str: ...

    async def delete_object(self, object_key: str) -> None: ...
