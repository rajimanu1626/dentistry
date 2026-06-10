"""boto3-based S3-compatible storage adapter.

Works identically against MinIO (dev), Supabase Storage (prod-Supabase), and
AWS S3 (prod-AWS). Endpoint, region and credentials are env-driven; nothing in
this file references a specific provider.
"""

from __future__ import annotations

import asyncio
import functools

import boto3
from botocore.client import Config

from app.adapters.storage.protocol import ObjectStorage, UploadedObject
from app.core.config import Settings


class S3Storage(ObjectStorage):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"},
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key.get_secret_value(),
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            config=config,
        )
        self._bucket = settings.s3_bucket

    async def put_object(
        self,
        *,
        object_key: str,
        body: bytes,
        mime_type: str,
    ) -> UploadedObject:
        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=object_key,
                Body=body,
                ContentType=mime_type,
            )

        await asyncio.get_running_loop().run_in_executor(None, _put)
        return UploadedObject(object_key=object_key, bytes_size=len(body), mime_type=mime_type)

    async def signed_get_url(self, object_key: str, *, ttl_seconds: int | None = None) -> str:
        ttl = ttl_seconds or self._settings.s3_signed_url_ttl_seconds
        return await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(
                self._client.generate_presigned_url,
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": object_key},
                ExpiresIn=ttl,
            ),
        )

    async def delete_object(self, object_key: str) -> None:
        await asyncio.get_running_loop().run_in_executor(
            None,
            functools.partial(self._client.delete_object, Bucket=self._bucket, Key=object_key),
        )
