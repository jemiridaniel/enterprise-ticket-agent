# app/services/graph_service.py
import time
from typing import Optional

import httpx
import msal

from ..config import settings


class GraphClient:
    """
    Thin wrapper around Microsoft Graph with client credentials flow.
    """

    def __init__(self):
        if not (settings.TENANT_ID and settings.CLIENT_ID and settings.CLIENT_SECRET):
            # We'll just operate in "disabled" mode if not configured.
            self.enabled = False
            self._app = None
            self._token_cache: dict | None = None
            return

        authority = f"https://login.microsoftonline.com/{settings.TENANT_ID}"
        self._app = msal.ConfidentialClientApplication(
            client_id=settings.CLIENT_ID,
            client_credential=settings.CLIENT_SECRET,
            authority=authority,
        )
        self._token_cache = {}
        self.enabled = True

    def _get_token(self) -> Optional[str]:
        """
        Gets a bearer token for Microsoft Graph.
        Very minimal caching just to avoid hitting AAD too often.
        """
        if not self.enabled or self._app is None:
            return None

        now = time.time()
        token_info = self._token_cache.get("token") if self._token_cache else None
        if token_info and token_info["expires_at"] > now + 60:
            return token_info["access_token"]

        result = self._app.acquire_token_for_client(
            scopes=[settings.GRAPH_SCOPE or "https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            # In a real app, log result["error"], result["error_description"], etc.
            return None

        access_token = result["access_token"]
        expires_in = result.get("expires_in", 300)
        self._token_cache["token"] = {
            "access_token": access_token,
            "expires_at": now + expires_in,
        }
        return access_token

    async def get(self, path: str, params: dict | None = None) -> Optional[dict]:
        """
        Minimal helper for GET /v1.0/{path} on Graph.
        """
        if not self.enabled:
            return None

        token = self._get_token()
        if not token:
            return None

        url = f"https://graph.microsoft.com/v1.0/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers, params=params)
        if resp.status_code >= 400:
            # In real-world, you'd log this.
            return None
        try:
            return resp.json()
        except Exception:
            return None


graph_client = GraphClient()
