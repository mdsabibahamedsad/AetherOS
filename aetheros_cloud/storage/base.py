"""Storage manager — pluggable cloud storage backends."""

from __future__ import annotations

import io
import json
import logging
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from aetheros_cloud.models import StorageBackend, StorageProvider, generate_id, now

logger = logging.getLogger(__name__)


class StorageManager:
    """Multi-backend cloud storage with read/write/list/delete.

    Adapter pattern: each provider implements the same interface.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self._data_dir = data_dir
        else:
            from aetheros_constants import get_aetheros_home
            self._data_dir = get_aetheros_home() / "cloud" / "storage"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._backends: Dict[str, StorageBackend] = {}
        self._adapters: Dict[str, Any] = {}
        self._local_root = self._data_dir / "local"
        self._local_root.mkdir(parents=True, exist_ok=True)
        self._load_backends()

    def register_backend(
        self,
        provider: StorageProvider,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        workspace_id: str = "",
        is_primary: bool = False,
    ) -> StorageBackend:
        backend = StorageBackend(
            id=generate_id("stor"),
            provider=provider,
            name=name,
            config=config or {},
            workspace_id=workspace_id,
            is_primary=is_primary,
            created_at=now(),
        )
        self._backends[backend.id] = backend
        adapter = self._create_adapter(backend)
        if adapter:
            self._adapters[backend.id] = adapter
        self._save_backends()
        logger.info("Registered storage backend %s (%s)", name, provider.value)
        return backend

    def get_backend(self, backend_id: str) -> Optional[StorageBackend]:
        return self._backends.get(backend_id)

    def list_backends(self, provider: Optional[StorageProvider] = None) -> List[StorageBackend]:
        if provider:
            return [b for b in self._backends.values() if b.provider == provider]
        return list(self._backends.values())

    def remove_backend(self, backend_id: str) -> bool:
        self._adapters.pop(backend_id, None)
        backend = self._backends.pop(backend_id, None)
        if backend:
            self._save_backends()
            return True
        return False

    def get_primary(self) -> Optional[StorageBackend]:
        for b in self._backends.values():
            if b.is_primary:
                return b
        return next(iter(self._backends.values())) if self._backends else None

    async def write(self, path: str, data: bytes, backend_id: Optional[str] = None) -> bool:
        backend = self._resolve_backend(backend_id)
        if backend is None:
            return False
        adapter = self._adapters.get(backend.id)
        if adapter and hasattr(adapter, "write"):
            return await adapter.write(path, data)
        return self._local_write(backend, path, data)

    async def read(self, path: str, backend_id: Optional[str] = None) -> Optional[bytes]:
        backend = self._resolve_backend(backend_id)
        if backend is None:
            return None
        adapter = self._adapters.get(backend.id)
        if adapter and hasattr(adapter, "read"):
            return await adapter.read(path)
        return self._local_read(backend, path)

    async def list(self, prefix: str = "", backend_id: Optional[str] = None) -> List[str]:
        backend = self._resolve_backend(backend_id)
        if backend is None:
            return []
        adapter = self._adapters.get(backend.id)
        if adapter and hasattr(adapter, "list"):
            return await adapter.list(prefix)
        return self._local_list(backend, prefix)

    async def delete(self, path: str, backend_id: Optional[str] = None) -> bool:
        backend = self._resolve_backend(backend_id)
        if backend is None:
            return False
        adapter = self._adapters.get(backend.id)
        if adapter and hasattr(adapter, "delete"):
            return await adapter.delete(path)
        return self._local_delete(backend, path)

    async def exists(self, path: str, backend_id: Optional[str] = None) -> bool:
        backend = self._resolve_backend(backend_id)
        if backend is None:
            return False
        adapter = self._adapters.get(backend.id)
        if adapter and hasattr(adapter, "exists"):
            return await adapter.exists(path)
        return self._local_exists(backend, path)

    def _resolve_backend(self, backend_id: Optional[str] = None) -> Optional[StorageBackend]:
        if backend_id:
            return self._backends.get(backend_id)
        return self.get_primary()

    def _create_adapter(self, backend: StorageBackend) -> Optional[Any]:
        try:
            if backend.provider == StorageProvider.S3:
                return self._create_s3_adapter(backend)
            elif backend.provider == StorageProvider.CLOUDFLARE_R2:
                return self._create_r2_adapter(backend)
            elif backend.provider == StorageProvider.GOOGLE_DRIVE:
                return self._create_gdrive_adapter(backend)
            elif backend.provider == StorageProvider.AZURE_BLOB:
                return self._create_azure_adapter(backend)
        except Exception as e:
            logger.warning("Failed to create adapter for %s: %s", backend.provider.value, e)
        return None

    def _create_s3_adapter(self, backend: StorageBackend) -> Any:
        import boto3
        session = boto3.Session(
            aws_access_key_id=backend.config.get("access_key"),
            aws_secret_access_key=backend.config.get("secret_key"),
            region_name=backend.config.get("region", "us-east-1"),
        )
        return _S3Adapter(session, backend.config.get("bucket", "aetheros"))

    def _create_r2_adapter(self, backend: StorageBackend) -> Any:
        import boto3
        session = boto3.Session(
            aws_access_key_id=backend.config.get("access_key"),
            aws_secret_access_key=backend.config.get("secret_key"),
        )
        return _S3Adapter(
            session,
            backend.config.get("bucket", "aetheros"),
            endpoint_url=backend.config.get("endpoint", f"https://{backend.config.get('account_id')}.r2.cloudflarestorage.com"),
        )

    def _create_gdrive_adapter(self, backend: StorageBackend) -> Any:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(token=backend.config.get("token"))
        service = build("drive", "v3", credentials=creds)
        return _GDriveAdapter(service)

    def _create_azure_adapter(self, backend: StorageBackend) -> Any:
        from azure.storage.blob import BlobServiceClient
        conn_str = backend.config.get("connection_string")
        client = BlobServiceClient.from_connection_string(conn_str)
        return _AzureAdapter(client, backend.config.get("container", "aetheros"))

    # ── Local fallback ──────────────────────────────────────────────

    def _local_write(self, backend: StorageBackend, path: str, data: bytes) -> bool:
        full = self._local_root / backend.id / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return True

    def _local_read(self, backend: StorageBackend, path: str) -> Optional[bytes]:
        full = self._local_root / backend.id / path
        return full.read_bytes() if full.exists() else None

    def _local_list(self, backend: StorageBackend, prefix: str) -> List[str]:
        root = self._local_root / backend.id / prefix
        if not root.exists():
            return []
        return [str(p.relative_to(self._local_root / backend.id)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]

    def _local_delete(self, backend: StorageBackend, path: str) -> bool:
        full = self._local_root / backend.id / path
        if full.exists():
            full.unlink()
            return True
        return False

    def _local_exists(self, backend: StorageBackend, path: str) -> bool:
        return (self._local_root / backend.id / path).exists()

    def _save_backends(self):
        path = self._data_dir / "backends.json"
        import dataclasses
        from enum import Enum
        def ser(obj):
            if dataclasses.is_dataclass(obj):
                return {f.name: ser(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, list):
                return [ser(v) for v in obj]
            if isinstance(obj, dict):
                return {k: ser(v) for k, v in obj.items()}
            return obj
        path.write_text(json.dumps([ser(b) for b in self._backends.values()], indent=2, default=str))

    def _load_backends(self):
        path = self._data_dir / "backends.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for d in data:
                try:
                    provider = StorageProvider(d.get("provider", "local"))
                except ValueError:
                    continue
                backend = StorageBackend(
                    id=d.get("id", ""),
                    provider=provider,
                    name=d.get("name", ""),
                    config=d.get("config", {}),
                    workspace_id=d.get("workspace_id", ""),
                    is_primary=d.get("is_primary", False),
                    created_at=d.get("created_at", 0.0),
                    last_verified=d.get("last_verified"),
                )
                self._backends[backend.id] = backend
                adapter = self._create_adapter(backend)
                if adapter:
                    self._adapters[backend.id] = adapter
        except Exception as e:
            logger.error("Failed to load storage backends: %s", e)


# ── Adapter implementations ─────────────────────────────────────────

class _S3Adapter:
    def __init__(self, session, bucket: str, endpoint_url: Optional[str] = None):
        self._client = session.client("s3", endpoint_url=endpoint_url)
        self._bucket = bucket

    async def write(self, path: str, data: bytes) -> bool:
        self._client.put_object(Bucket=self._bucket, Key=path, Body=data)
        return True

    async def read(self, path: str) -> Optional[bytes]:
        obj = self._client.get_object(Bucket=self._bucket, Key=path)
        return obj["Body"].read()

    async def list(self, prefix: str) -> List[str]:
        resp = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return [o["Key"] for o in resp.get("Contents", [])]

    async def delete(self, path: str) -> bool:
        self._client.delete_object(Bucket=self._bucket, Key=path)
        return True

    async def exists(self, path: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=path)
            return True
        except Exception:
            return False


class _GDriveAdapter:
    def __init__(self, service):
        self._service = service

    async def write(self, path: str, data: bytes) -> bool:
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/octet-stream")
        file_metadata = {"name": path, "parents": []}
        self._service.files().create(body=file_metadata, media_body=media).execute()
        return True

    async def read(self, path: str) -> Optional[bytes]:
        results = self._service.files().list(q=f"name='{path}'", fields="files(id)").execute()
        files = results.get("files", [])
        if not files:
            return None
        data = self._service.files().get_media(fileId=files[0]["id"]).execute()
        return data

    async def list(self, prefix: str) -> List[str]:
        results = self._service.files().list(q=f"name contains '{prefix}'", fields="files(name)").execute()
        return [f["name"] for f in results.get("files", [])]

    async def delete(self, path: str) -> bool:
        results = self._service.files().list(q=f"name='{path}'", fields="files(id)").execute()
        for f in results.get("files", []):
            self._service.files().delete(fileId=f["id"]).execute()
        return True

    async def exists(self, path: str) -> bool:
        results = self._service.files().list(q=f"name='{path}'", fields="files(id)").execute()
        return bool(results.get("files", []))


class _AzureAdapter:
    def __init__(self, client, container: str):
        self._client = client
        self._container = container

    async def write(self, path: str, data: bytes) -> bool:
        blob = self._client.get_blob_client(container=self._container, blob=path)
        blob.upload_blob(data, overwrite=True)
        return True

    async def read(self, path: str) -> Optional[bytes]:
        blob = self._client.get_blob_client(container=self._container, blob=path)
        return blob.download_blob().readall()

    async def list(self, prefix: str) -> List[str]:
        container_client = self._client.get_container_client(self._container)
        return [b.name for b in container_client.list_blobs(name_starts_with=prefix)]

    async def delete(self, path: str) -> bool:
        blob = self._client.get_blob_client(container=self._container, blob=path)
        blob.delete_blob()
        return True

    async def exists(self, path: str) -> bool:
        blob = self._client.get_blob_client(container=self._container, blob=path)
        return blob.exists()
