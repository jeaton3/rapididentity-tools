"""
Main RapidIdentity Connect API
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from rapididentity.utils.helpers import normalize_payload

if TYPE_CHECKING:
    from rapididentity.client import RapidIdentityClient


class RapidIdentityConnect:
    """
    Main client for interacting with RapidIdentity Connect APIs.

    Facade for interacting with RapidIdentity Connect REST API endpoints.
    Reuses an existing RapidIdentityClient instance.
    """

    def __init__(
        self,
        client: "RapidIdentityClient",
        actions_path: str = "/admin/connect/actions",
    ) -> None:
        self.client = client
        self.actions_path = actions_path

    # `normalize_payload` is provided from rapididentity.utils.helpers
    # and used below; kept as a module-level helper to allow reuse.

    def _connect_path(self, endpoint: str) -> str:
        """Build an absolute /admin/connect path from a relative or absolute endpoint."""
        if endpoint.startswith("/admin/connect/"):
            return endpoint
        if endpoint == "/admin/connect":
            return endpoint

        trimmed = endpoint.strip("/")
        return f"/admin/connect/{trimmed}" if trimmed else "/admin/connect"

    def get(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        **params: Any,
    ) -> Any:
        """(Removed) Use `client.get()` with a `/admin/connect/...` path instead."""

    def post_action(
        self,
        action_xml: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """POST an actionDef XML payload to /admin/connect/actions."""
        request_headers = {
            "Content-Type": "application/xml",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        payload = self.client.request(
            "POST",
            self.actions_path,
            raw_data=action_xml,
            headers=request_headers,
        )
        return normalize_payload(payload)

    def get_actions(
        self,
        project: Optional[str] = None,
        metaDataOnly: Optional[bool] = None,
        **filters: Any,
    ) -> Any:
        """
        Get available Connect actions.

        Args:
            project: Optional project name or ID to filter actions.
            metaDataOnly: Optional flag to return metadata only.
            **filters: Additional query string filters.
        """
        params: Dict[str, Any] = {}

        if project:
            params["project"] = project

        if metaDataOnly is not None:
            params["metaDataOnly"] = str(metaDataOnly).lower()

        params.update(filters)

        payload = self.client.get(self.actions_path, params=params)
        return normalize_payload(payload, list_key="actions")
    
    def get_adapters(self) -> Any:
        """
        Get available Connect adapters.
        """

        payload = self.client.get("/admin/connect/adapters")
        return normalize_payload(payload, list_key="adapters")

    def get_actionset_history(
        self, actionset_id: str, version: Optional[str] = None
    ) -> Any:
        """
        Fetch action set history or a specific version.

        - If `version` is None: returns the endpoint payload from
          `/admin/connect/actionSetHistory/{actionset_id}` (may be JSON/list).
        - If `version` is provided: returns the XML string for
          `/admin/connect/actionSetHistory/{actionset_id}/{version}`.
        """
        base = f"/admin/connect/actionSetHistory/{actionset_id}"
        if version:
            path = f"{base}/{version}"
            headers = {"Accept": "*/*"}
            payload = self.client.get(path, params=None, headers=headers)

            # Unwrap common response shapes to extract XML string
            if isinstance(payload, str):
                return payload
            if isinstance(payload, dict):
                for key in ("xml", "actionDef", "actionSetVersion", "payload"):
                    v = payload.get(key)
                    if isinstance(v, str):
                        return v
                data = payload.get("data")
                if isinstance(data, str):
                    return data
                if isinstance(data, dict):
                    for key in ("xml", "actionDef", "actionSetVersion"):
                        v = data.get(key)
                        if isinstance(v, str):
                            return v

            raise ValueError("Expected XML string payload from actionSetHistory endpoint")

        # No version requested - return the raw payload so callers can inspect
        # versions/history in whichever shape the API returns.
        return self.client.get(base)

    def get_files(
        self, path: Optional[str] = None, project: Optional[str] = None
    ) -> Any:
        """
        List file/directory entries using the Connect `files` endpoints.

        If `path` is provided calls `/admin/connect/files/{path}`, otherwise
        calls `/admin/connect/files`. Returns the normalized payload (list
        of entries when available).
        """
        params: Dict[str, Any] = {}
        if project:
            params["project"] = project

        if path:
            endpoint = f"/admin/connect/files/{path}"
        else:
            endpoint = "/admin/connect/files"

        headers = {"Accept": "application/json"}
        payload = self.client.get(endpoint, params=params, headers=headers)
        return normalize_payload(payload, list_key="files")

    def get_file_content(self, path: str, project: Optional[str] = None) -> Any:
        """
        Fetch the contents of a file using Connect `fileContent` endpoints.

        Calls `/admin/connect/fileContent/{path}` (or the query form) and
        returns the inner `data` field when present (a string), otherwise
        returns the normalized payload.
        """
        params: Dict[str, Any] = {}
        if project:
            params["project"] = project

        endpoint = f"/admin/connect/fileContent/{path}"
        headers = {"Accept": "application/json"}
        payload = self.client.get(endpoint, params=params, headers=headers)
        normalized = normalize_payload(payload)

        if isinstance(normalized, dict):
            # Many Connect endpoints wrap the file body in a `data` field.
            data = normalized.get("data")
            if data is not None:
                return data

        return normalized