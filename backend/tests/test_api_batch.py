import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_sample(client: AsyncClient, count: int = 3) -> list[str]:
    items = [
        {"email": f"user{i}@outlook.com", "password": f"pass{i}", "client_id": f"cid{i}", "refresh_token": f"rt{i}"}
        for i in range(count)
    ]
    await client.post("/api/mailboxes/import", json={"items": items, "mode": "append"})
    resp = await client.get("/api/mailboxes")
    return [m["id"] for m in resp.json()["items"]]


class TestBatchDelete:
    async def test_batch_delete(self, client: AsyncClient):
        ids = await _import_sample(client, 3)
        resp = await client.request("DELETE", "/api/mailboxes/batch", json={"ids": ids[:2]})
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2
        listing = await client.get("/api/mailboxes")
        assert listing.json()["total"] == 1


class TestBatchSetGroup:
    async def test_batch_set_group(self, client: AsyncClient):
        ids = await _import_sample(client, 2)
        grp = await client.post("/api/groups", json={"name": "BatchGrp"})
        gid = grp.json()["id"]
        resp = await client.patch("/api/mailboxes/batch/group", json={"ids": ids, "group_id": gid})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2
        listing = await client.get(f"/api/mailboxes?group_id={gid}")
        assert listing.json()["total"] == 2


class TestBatchCopy:
    async def test_copy_emails(self, client: AsyncClient):
        ids = await _import_sample(client, 2)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "email"})
        assert resp.status_code == 200
        text = resp.json()["text"]
        assert "user0@outlook.com" in text or "user1@outlook.com" in text

    async def test_copy_passwords(self, client: AsyncClient):
        ids = await _import_sample(client, 1)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "password"})
        assert resp.status_code == 200
        assert "pass0" in resp.json()["text"]

    async def test_copy_combined(self, client: AsyncClient):
        ids = await _import_sample(client, 1)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "combined"})
        text = resp.json()["text"]
        assert "----" in text
        assert "user0@outlook.com" in text
