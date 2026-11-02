"""Marketplace endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    response = await client.get("/api/v1/categories/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_marketplace_agents_empty(client: AsyncClient):
    response = await client.get("/api/v1/marketplace/agents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_marketplace_search(client: AsyncClient):
    response = await client.get("/api/v1/marketplace/agents?search=research")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_marketplace_agent_not_found(client: AsyncClient):
    response = await client.get("/api/v1/marketplace/agents/nonexistent-id")
    assert response.status_code == 404
