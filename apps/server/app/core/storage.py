from __future__ import annotations

from typing import BinaryIO

import boto3
import requests

from app.core.config import settings


class StorageClient:
    def __init__(self) -> None:
        endpoint = settings.s3_endpoint or ""
        self._is_supabase = "supabase.co" in endpoint
        if self._is_supabase:
            self._client = None
            self._session = requests.Session()
        else:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
            )
            self._session = None
        self._bucket = settings.s3_bucket

    def upload_file(self, key: str, fileobj: BinaryIO, content_type: str) -> str:
        if self._is_supabase:
            data = fileobj.read()
            return self._supabase_put_bytes(key, data, content_type)

        assert self._client is not None
        self._client.upload_fileobj(
            fileobj,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"{settings.s3_endpoint}/{self._bucket}/{key}"

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        if self._is_supabase:
            return self._supabase_put_bytes(key, data, content_type)

        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return f"{settings.s3_endpoint}/{self._bucket}/{key}"
        except Exception as e:
            print(f"❌ Storage upload failed: {type(e).__name__}: {str(e)}")
            # Return a data URL as fallback
            import base64

            encoded = base64.b64encode(data).decode()
            return f"data:{content_type};base64,{encoded}"

    def _supabase_put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        endpoint = settings.s3_endpoint.rstrip("/")
        url = f"{endpoint}/object/{self._bucket}/{key}"
        headers = {
            "Authorization": f"Bearer {settings.s3_secret_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }
        response = self._session.post(url, headers=headers, data=data)
        try:
            response.raise_for_status()
        except Exception as exc:
            print(
                f"❌ Supabase storage upload failed: {type(exc).__name__}: {str(exc)}"
            )
            import base64

            encoded = base64.b64encode(data).decode()
            return f"data:{content_type};base64,{encoded}"

        # make asset publicly accessible
        return f"{endpoint}/object/public/{self._bucket}/{key}"


storage_client = StorageClient()
