from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

MOCK_LIST_RESPONSE = {
    "value": [
        {
            "id": "msg-001",
            "subject": "Test Email",
            "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
            "bodyPreview": "Hello world...",
            "receivedDateTime": "2026-05-23T10:00:00Z",
            "isRead": False,
        }
    ]
}

MOCK_BODY_RESPONSE = {
    "id": "msg-001",
    "subject": "Test Email",
    "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
    "receivedDateTime": "2026-05-23T10:00:00Z",
    "body": {"contentType": "html", "content": "<p>Hello <script>alert(1)</script></p>"},
}


async def _import_one(client: AsyncClient) -> str:
    await client.post(
        "/api/mailboxes/import",
        json={
            "items": [{"email": "test@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"}],
            "mode": "append",
        },
    )
    listing = await client.get("/api/mailboxes")
    return listing.json()["items"][0]["id"]


class TestEmailListAPI:
    @patch("app.api.emails.GraphClient")
    async def test_list_emails(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value
        instance.list_emails = AsyncMock(return_value=MOCK_LIST_RESPONSE)

        resp = await client.get(f"/api/mailboxes/{mid}/emails?folder=inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Test Email"
        assert data[0]["sender_name"] == "Sender"


class TestEmailDetailAPI:
    @patch("app.api.emails.GraphClient")
    async def test_get_email_body_sanitized(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value
        instance.get_email_body = AsyncMock(return_value=MOCK_BODY_RESPONSE)

        resp = await client.get(f"/api/mailboxes/{mid}/emails/msg-001")
        assert resp.status_code == 200
        data = resp.json()
        assert "<script>" not in data["body_html"]
        assert "Hello" in data["body_html"]
