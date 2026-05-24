import asyncio

import httpx
import msal
from redis.asyncio import Redis

from app.config import settings

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/.default"]

GRAPH_TIMEOUT = httpx.Timeout(30.0)


class GraphClient:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def _get_access_token(
        self, client_id: str, refresh_token: str, mailbox_id: str
    ) -> str:
        cache_key = f"access_token:{mailbox_id}"
        cached = await self._redis.get(cache_key)
        if cached:
            return cached.decode()

        app = msal.PublicClientApplication(client_id=client_id)
        result = await asyncio.to_thread(
            app.acquire_token_by_refresh_token, refresh_token, scopes=SCOPES
        )

        if "access_token" not in result:
            raise ValueError(
                f"Token refresh failed: {result.get('error_description', 'unknown')}"
            )

        token = result["access_token"]
        await self._redis.setex(cache_key, settings.ACCESS_TOKEN_CACHE_TTL, token)
        return token

    async def list_emails(
        self,
        client_id: str,
        refresh_token: str,
        mailbox_id: str,
        folder: str = "inbox",
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> dict:
        token = await self._get_access_token(client_id, refresh_token, mailbox_id)
        skip = (page - 1) * page_size

        folder_map = {"inbox": "Inbox", "junk": "JunkEmail"}
        folder_name = folder_map.get(folder, "Inbox")

        url = f"{GRAPH_BASE}/me/mailFolders/{folder_name}/messages"
        params = {
            "$top": page_size,
            "$skip": skip,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,bodyPreview,receivedDateTime,isRead",
        }
        headers = {"Authorization": f"Bearer {token}"}
        if search:
            params["$search"] = f'"{search}"'
            headers["ConsistencyLevel"] = "eventual"

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_email_body(
        self, client_id: str, refresh_token: str, mailbox_id: str, message_id: str
    ) -> dict:
        token = await self._get_access_token(client_id, refresh_token, mailbox_id)
        url = f"{GRAPH_BASE}/me/messages/{message_id}"
        params = {"$select": "id,subject,from,receivedDateTime,body"}

        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def validate_token(self, client_id: str, refresh_token: str) -> bool:
        try:
            app = msal.PublicClientApplication(client_id=client_id)
            result = await asyncio.to_thread(
                app.acquire_token_by_refresh_token, refresh_token, scopes=SCOPES
            )
            return "access_token" in result
        except Exception:
            return False
