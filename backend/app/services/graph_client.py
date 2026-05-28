import asyncio
import logging
from typing import Optional

import httpx
import msal
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/Mail.Read"]

GRAPH_TIMEOUT = httpx.Timeout(30.0)


class GraphClient:
    def __init__(self, redis: Optional[Redis]):
        self._redis = redis

    async def _get_access_token(
        self, client_id: str, refresh_token: str, mailbox_id: str,
        *, force_refresh: bool = False,
    ) -> str:
        cache_key = f"access_token:{mailbox_id}"
        if not force_refresh and self._redis is not None:
            try:
                cached = await self._redis.get(cache_key)
            except Exception as exc:
                logger.warning("Redis cache get failed for mailbox %s: %s", mailbox_id, exc)
                cached = None
            if cached:
                return cached.decode()

        app = msal.PublicClientApplication(client_id=client_id)
        result = await asyncio.to_thread(
            app.acquire_token_by_refresh_token, refresh_token, scopes=SCOPES
        )

        if "access_token" not in result:
            logger.error(
                "MSAL token refresh failed for mailbox %s: %s",
                mailbox_id, result.get("error_description", result),
            )
            raise ValueError(
                f"Token refresh failed: {result.get('error_description', 'unknown')}"
            )

        token = result["access_token"]
        if self._redis is not None:
            try:
                await self._redis.setex(cache_key, settings.ACCESS_TOKEN_CACHE_TTL, token)
            except Exception as exc:
                logger.warning("Redis cache set failed for mailbox %s: %s", mailbox_id, exc)
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
            if resp.status_code == 401:
                logger.warning("Graph 401 for mailbox %s, retrying with fresh token", mailbox_id)
                token = await self._get_access_token(
                    client_id, refresh_token, mailbox_id, force_refresh=True,
                )
                headers["Authorization"] = f"Bearer {token}"
                resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_email_body(
        self, client_id: str, refresh_token: str, mailbox_id: str, message_id: str
    ) -> dict:
        token = await self._get_access_token(client_id, refresh_token, mailbox_id)
        url = f"{GRAPH_BASE}/me/messages/{message_id}"
        params = {"$select": "id,subject,from,receivedDateTime,body"}

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 401:
                logger.warning("Graph 401 for mailbox %s, retrying with fresh token", mailbox_id)
                token = await self._get_access_token(
                    client_id, refresh_token, mailbox_id, force_refresh=True,
                )
                headers["Authorization"] = f"Bearer {token}"
                resp = await client.get(url, headers=headers, params=params)
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
