import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_sample(client: AsyncClient, count: int = 3) -> dict:
    items = [
        {
            "email": f"user{i}@outlook.com",
            "password": f"pass{i}",
            "client_id": f"cid{i}",
            "refresh_token": f"rt{i}",
        }
        for i in range(count)
    ]
    resp = await client.post("/api/mailboxes/import", json={"items": items, "mode": "append"})
    return resp.json()


class TestMailboxList:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/api/mailboxes?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_with_pagination(self, client: AsyncClient):
        await _import_sample(client, 5)
        resp = await client.get("/api/mailboxes?page=1&page_size=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_search_by_email(self, client: AsyncClient):
        await _import_sample(client, 3)
        resp = await client.get("/api/mailboxes?search=user1")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "user1@outlook.com"

    async def test_list_filter_by_group(self, client: AsyncClient):
        grp = await client.post("/api/groups", json={"name": "TestGrp"})
        gid = grp.json()["id"]
        await _import_sample(client, 2)
        listing = await client.get("/api/mailboxes")
        mid = listing.json()["items"][0]["id"]
        await client.patch("/api/mailboxes/batch/group", json={"ids": [mid], "group_id": gid})
        resp = await client.get(f"/api/mailboxes?group_id={gid}")
        assert resp.json()["total"] == 1


class TestMailboxImport:
    async def test_append_import(self, client: AsyncClient):
        result = await _import_sample(client, 3)
        assert result["imported"] == 3
        assert result["skipped"] == 0

    async def test_import_dedup_skips_existing(self, client: AsyncClient):
        await _import_sample(client, 2)
        resp = await client.post(
            "/api/mailboxes/import",
            json={
                "items": [
                    {"email": "user0@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                    {"email": "new@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                ],
                "mode": "append",
            },
        )
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    async def test_overwrite_import(self, client: AsyncClient):
        await _import_sample(client, 3)
        resp = await client.post(
            "/api/mailboxes/import",
            json={
                "items": [
                    {"email": "only@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                ],
                "mode": "overwrite",
            },
        )
        assert resp.json()["imported"] == 1
        listing = await client.get("/api/mailboxes")
        assert listing.json()["total"] == 1


class TestMailboxDelete:
    async def test_delete_single(self, client: AsyncClient):
        await _import_sample(client, 1)
        listing = await client.get("/api/mailboxes")
        mid = listing.json()["items"][0]["id"]
        resp = await client.delete(f"/api/mailboxes/{mid}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_404(self, client: AsyncClient):
        resp = await client.delete("/api/mailboxes/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestMailboxExport:
    async def test_export_csv(self, client: AsyncClient):
        await _import_sample(client, 2)
        resp = await client.post(
            "/api/mailboxes/export",
            json={"format": "csv", "include_all": True},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
