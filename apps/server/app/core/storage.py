from __future__ import annotations

from typing import BinaryIO

import boto3

from app.core.config import settings


class StorageClient:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        self._bucket = settings.s3_bucket

    def upload_file(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        self._client.upload_fileobj(
            fileobj,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"{settings.s3_endpoint}/{self._bucket}/{key}"

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            # For Supabase storage, use the proper URL format
            if "supabase" in settings.s3_endpoint:
                return f"{settings.s3_endpoint}/object/public/{self._bucket}/{key}"
            return f"{settings.s3_endpoint}/{self._bucket}/{key}"
        except Exception as e:
            print(f"❌ Storage upload failed: {type(e).__name__}: {str(e)}")
            # Return a data URL as fallback
            import base64

            encoded = base64.b64encode(data).decode()
            return f"data:{content_type};base64,{encoded}"


storage_client = StorageClient()
