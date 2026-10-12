"""AetherOS Integrations — cloud storage adapters.

Google Drive, Dropbox, OneDrive, Box, Nextcloud, WebDAV, and S3. Upload,
download, search, and sync-aware listing.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional

import httpx

from aetheros_integrations.models import AuthMethod, HealthStatus, IntegrationCategory, ProviderDefinition
from aetheros_integrations.providers.base import RESTProvider, register_provider

logger = logging.getLogger(__name__)


@register_provider
class GoogleDriveProvider(RESTProvider):
    definition = ProviderDefinition(
        key="google_drive",
        category=IntegrationCategory.STORAGE,
        display_name="Google Drive",
        description="Google Drive API: upload, download, search.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://www.googleapis.com/drive/v3",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        capabilities=["upload_file", "download_file", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/about", headers=self._headers(), params={"fields": "user"}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_files(self, query: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        params = {"pageSize": max_results, "fields": "files(id,name,mimeType,size)"}
        if query:
            params["q"] = query
        resp = httpx.get(f"{self.definition.base_url}/files", headers=self._headers(), params=params, timeout=15)
        return resp.json().get("files", []) if resp.status_code == 200 else []

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        return self.list_files(query=f"name contains '{query}'", max_results=max_results)

    def upload_file(self, name: str, data: bytes, mime_type: str = "application/octet-stream", **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no drive credential"}
        metadata = {"name": name, "mimeType": mime_type}
        files = {"metadata": (None, str(metadata).replace("'", '"'), "application/json"), "file": (name, data, mime_type)}
        resp = httpx.post(
            f"{self.definition.base_url}/files?uploadType=multipart",
            headers=self._headers(),
            files=files,
            timeout=30,
        )
        return {"success": resp.status_code == 200, "status": resp.status_code, "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}}

    def download_file(self, file_id: str, **kwargs) -> Optional[bytes]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return None
        resp = httpx.get(f"{self.definition.base_url}/files/{file_id}?alt=media", headers=self._headers(), timeout=30)
        return resp.content if resp.status_code == 200 else None


@register_provider
class DropboxProvider(RESTProvider):
    definition = ProviderDefinition(
        key="dropbox",
        category=IntegrationCategory.STORAGE,
        display_name="Dropbox",
        description="Dropbox API v2: upload, download, list.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://api.dropboxapi.com/2",
        scopes=["files.content.write", "files.content.read", "files.metadata.read"],
        capabilities=["upload_file", "download_file", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.post(f"{self.definition.base_url}/users/get_current_account", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_files(self, path: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.post(f"{self.definition.base_url}/files/list_folder", headers={**self._headers(), "Content-Type": "application/json"}, json={"path": path or "", "limit": max_results}, timeout=15)
        return resp.json().get("entries", []) if resp.status_code == 200 else []

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.post(f"{self.definition.base_url}/files/search_v2", headers={**self._headers(), "Content-Type": "application/json"}, json={"query": query, "max_results": max_results}, timeout=15)
        matches = resp.json().get("matches", []) if resp.status_code == 200 else []
        return [m.get("metadata", {}).get("metadata", {}) for m in matches]

    def upload_file(self, name: str, data: bytes, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no dropbox credential"}
        path = kwargs.get("path", "/") + name
        commit = {"path": path, "mode": "add", "autorename": True, "mute": False}
        headers = {**self._headers(), "Content-Type": "application/octet-stream", "Dropbox-API-Arg": str(commit).replace("'", '"')}
        resp = httpx.post(f"{self.definition.base_url}/files/upload", headers=headers, content=data, timeout=30)
        return {"success": resp.status_code == 200, "status": resp.status_code}


@register_provider
class OneDriveProvider(RESTProvider):
    definition = ProviderDefinition(
        key="onedrive",
        category=IntegrationCategory.STORAGE,
        display_name="OneDrive",
        description="OneDrive via Graph API.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://graph.microsoft.com/v1.0",
        scopes=["Files.ReadWrite.All"],
        capabilities=["upload_file", "download_file", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        return HealthStatus.HEALTHY if token.startswith("Bearer") else HealthStatus.UNHEALTHY

    def list_files(self, path: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        url = f"{self.definition.base_url}/me/drive/root:{path or ''}:/children" if path else f"{self.definition.base_url}/me/drive/root/children"
        resp = httpx.get(url, headers=self._headers(), params={"$top": max_results}, timeout=15)
        return resp.json().get("value", []) if resp.status_code == 200 else []

    def upload_file(self, name: str, data: bytes, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no onedrive credential"}
        path = kwargs.get("path", "") + "/" + name
        resp = httpx.put(f"{self.definition.base_url}/me/drive/root:{path}:/content", headers=self._headers(), content=data, timeout=30)
        return {"success": resp.status_code in (200, 201), "status": resp.status_code}


@register_provider
class BoxProvider(RESTProvider):
    definition = ProviderDefinition(
        key="box",
        category=IntegrationCategory.STORAGE,
        display_name="Box",
        description="Box API v2: upload, download, list.",
        auth_method=AuthMethod.OAUTH2,
        base_url="https://api.box.com/2.0",
        scopes=["root_readwrite"],
        capabilities=["upload_file", "download_file", "search"],
    )

    def ping(self) -> HealthStatus:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return HealthStatus.UNAVAILABLE
        try:
            resp = httpx.get(f"{self.definition.base_url}/users/me", headers=self._headers(), timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (httpx.HTTPError, OSError):
            return HealthStatus.DEGRADED

    def list_files(self, folder_id: str = "0", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return []
        resp = httpx.get(f"{self.definition.base_url}/folders/{folder_id}/items", headers=self._headers(), params={"limit": max_results}, timeout=15)
        return resp.json().get("entries", []) if resp.status_code == 200 else []

    def upload_file(self, name: str, data: bytes, **kwargs) -> Dict[str, Any]:
        token = self.config.get("_auth_header", {}).get("Authorization", "")
        if not token:
            return {"success": False, "error": "no box credential"}
        folder_id = kwargs.get("folder_id", "0")
        resp = httpx.post(
            f"{self.definition.base_url}/files/content",
            headers=self._headers(),
            data={"attributes": f'{{"name":"{name}","parent":{{"id":"{folder_id}"}}}}'},
            files={"file": (name, data)},
            timeout=30,
        )
        return {"success": resp.status_code == 201, "status": resp.status_code}


@register_provider
class NextcloudProvider(RESTProvider):
    definition = ProviderDefinition(
        key="nextcloud",
        category=IntegrationCategory.STORAGE,
        display_name="Nextcloud",
        description="Nextcloud WebDAV + OCS API.",
        auth_method=AuthMethod.BASIC,
        base_url="",
        capabilities=["upload_file", "download_file", "search"],
    )

    def _base(self) -> str:
        return self.config.get("server_url", "")

    def _auth(self):
        return (self.config.get("username", ""), self.config.get("password", ""))

    def ping(self) -> HealthStatus:
        base = self._base()
        if not base:
            return HealthStatus.UNAVAILABLE
        try:
            import requests

            resp = requests.get(base.rstrip("/") + "/ocs/v1.php/cloud/capabilities", auth=self._auth(), headers={"OCS-APIRequest": "true"}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code == 200 else HealthStatus.UNHEALTHY
        except (requests.RequestException, OSError):
            return HealthStatus.DEGRADED

    def list_files(self, path: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        import requests

        base = self._base()
        if not base:
            return []
        url = base.rstrip("/") + "/remote.php/dav/files/" + self.config.get("username", "") + (f"/{path}" if path else "")
        resp = requests.request("PROPFIND", url, auth=self._auth(), data="""<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:displayname/><d:getcontentlength/></d:prop></d:propfind>""", headers={"Depth": "1"}, timeout=20)
        if resp.status_code not in (200, 207):
            return []
        return [{"href": h} for h in _hrefs(resp.text)][:max_results]

    def upload_file(self, name: str, data: bytes, **kwargs) -> Dict[str, Any]:
        import requests

        base = self._base()
        username = self.config.get("username", "")
        if not base or not username:
            return {"success": False, "error": "no nextcloud config"}
        path = kwargs.get("path", "")
        url = base.rstrip("/") + "/remote.php/dav/files/" + username + f"/{path}/{name}".replace("//", "/")
        resp = requests.put(url, auth=self._auth(), data=data, timeout=30)
        return {"success": resp.status_code in (200, 201, 204), "status": resp.status_code}


@register_provider
class WebDAVProvider(RESTProvider):
    definition = ProviderDefinition(
        key="webdav",
        category=IntegrationCategory.STORAGE,
        display_name="WebDAV",
        description="Generic WebDAV server: list, upload, download.",
        auth_method=AuthMethod.BASIC,
        base_url="",
        capabilities=["upload_file", "download_file", "search"],
    )

    def _base(self) -> str:
        return self.config.get("dav_url", "")

    def _auth(self):
        return (self.config.get("dav_user", ""), self.config.get("dav_password", ""))

    def ping(self) -> HealthStatus:
        import requests

        base = self._base()
        if not base:
            return HealthStatus.UNAVAILABLE
        try:
            resp = requests.request("PROPFIND", base.rstrip("/") + "/", auth=self._auth(), headers={"Depth": "0"}, timeout=10)
            return HealthStatus.HEALTHY if resp.status_code in (200, 207) else HealthStatus.UNHEALTHY
        except (requests.RequestException, OSError):
            return HealthStatus.DEGRADED

    def list_files(self, path: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        import requests

        base = self._base()
        if not base:
            return []
        url = base.rstrip("/") + (f"/{path}" if path else "")
        resp = requests.request("PROPFIND", url, auth=self._auth(), headers={"Depth": "1"}, timeout=20)
        if resp.status_code not in (200, 207):
            return []
        return [{"href": h} for h in _hrefs(resp.text)][:max_results]

    def upload_file(self, name: str, data: bytes, **kwargs) -> Dict[str, Any]:
        import requests

        base = self._base()
        if not base:
            return {"success": False, "error": "no webdav url"}
        path = kwargs.get("path", "")
        url = base.rstrip("/") + (f"/{path}" if path else "") + f"/{name}"
        resp = requests.put(url, auth=self._auth(), data=data, timeout=30)
        return {"success": resp.status_code in (200, 201, 204), "status": resp.status_code}


@register_provider
class S3Provider(RESTProvider):
    definition = ProviderDefinition(
        key="s3",
        category=IntegrationCategory.STORAGE,
        display_name="S3",
        description="Amazon S3-compatible object storage (boto3 optional).",
        auth_method=AuthMethod.API_KEY,
        base_url="",
        capabilities=["upload_file", "download_file", "search"],
    )

    def _client(self):
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 integration") from exc
        return boto3.client(
            "s3",
            aws_access_key_id=self.config.get("access_key", ""),
            aws_secret_access_key=self.config.get("secret_key", ""),
            region_name=self.config.get("region", "us-east-1"),
            endpoint_url=self.config.get("endpoint_url", "") or None,
            config=Config(signature_version="s3v4"),
        )

    def ping(self) -> HealthStatus:
        if not self.config.get("access_key") or not self.config.get("secret_key"):
            return HealthStatus.UNAVAILABLE
        try:
            client = self._client()
            client.list_buckets()
            return HealthStatus.HEALTHY
        except RuntimeError:
            return HealthStatus.UNAVAILABLE
        except Exception:  # noqa: BLE001
            return HealthStatus.UNHEALTHY

    def list_files(self, bucket: str, prefix: str = "", max_results: int = 20, **kwargs) -> List[Dict[str, Any]]:
        if not self.config.get("access_key"):
            return []
        try:
            client = self._client()
            resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_results)
            return resp.get("Contents", [])
        except RuntimeError:
            return []

    def upload_file(self, name: str, data: bytes, bucket: str = "", **kwargs) -> Dict[str, Any]:
        if not bucket:
            bucket = self.config.get("bucket", "")
        if not bucket:
            return {"success": False, "error": "no s3 bucket"}
        try:
            client = self._client()
            client.put_object(Bucket=bucket, Key=name, Body=data)
            return {"success": True}
        except RuntimeError as exc:
            return {"success": False, "error": str(exc)}


def _hrefs(xml_text: str) -> List[str]:
    import re

    return re.findall(r"<[dD]:href[^>]*>([^<]+)</[dD]:href>", xml_text)
