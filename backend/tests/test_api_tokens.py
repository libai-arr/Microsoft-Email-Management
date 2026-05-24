import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_one(client: AsyncClient) -> str:
    await client.post(
        "/api/mailboxes/import",
        json={
            "items": [{"email": "t@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"}],
            "mode": "append",
        },
    )
    listing = await client.get("/api/mailboxes")
    return listing.json()["items"][0]["id"]


class TestTokenStatusAPI:
    async def test_get_status(self, client: AsyncClient):
        mid = await _import_one(client)
        resp = await client.get(f"/api/tokens/status?ids={mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "normal"

    async def test_trigger_check(self, client: AsyncClient):
        mid = await _import_one(client)
        resp = await client.post("/api/tokens/check", json={"ids": [mid]})
        assert resp.status_code == 200
        assert resp.json()["queued"] == 1
        status = await client.get(f"/api/tokens/status?ids={mid}")
        assert status.json()[0]["status"] == "checking"
