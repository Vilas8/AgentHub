"""Authentication endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass1",
        "full_name": "Test User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "customer"
    assert "access_token" not in data  # tokens in cookies, not body


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "TestPass1", "full_name": "Dup User"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "short",
        "full_name": "Weak User",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "LoginPass1",
        "full_name": "Login User",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "LoginPass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpw@example.com",
        "password": "CorrectPass1",
        "full_name": "Wrong PW",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "WrongPassword1",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
