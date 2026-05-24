import pytest
import pytest_asyncio
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestGroupsAPI:
    async def test_list_groups_empty(self, client: AsyncClient):
        resp = await client.get("/api/groups")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_group(self, client: AsyncClient):
        resp = await client.post("/api/groups", json={"name": "营销A组"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "营销A组"
        assert data["mailbox_count"] == 0
        assert "id" in data

    async def test_create_duplicate_group_fails(self, client: AsyncClient):
        await client.post("/api/groups", json={"name": "Test"})
        resp = await client.post("/api/groups", json={"name": "Test"})
        assert resp.status_code == 409

    async def test_update_group(self, client: AsyncClient):
        create = await client.post("/api/groups", json={"name": "Old"})
        gid = create.json()["id"]
        resp = await client.put(f"/api/groups/{gid}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    async def test_delete_group(self, client: AsyncClient):
        create = await client.post("/api/groups", json={"name": "ToDelete"})
        gid = create.json()["id"]
        resp = await client.delete(f"/api/groups/{gid}")
        assert resp.status_code == 204
        listing = await client.get("/api/groups")
        assert len(listing.json()) == 0

    async def test_delete_nonexistent_group_404(self, client: AsyncClient):
        resp = await client.delete("/api/groups/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
