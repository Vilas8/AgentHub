"""Security tests: Refresh tokens, revocation, CSRF, and session protection."""
import pytest
from httpx import AsyncClient



@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client: AsyncClient):
    # 1. Register user
    reg = await client.post("/api/v1/auth/register", json={
        "email": "rotator@example.com",
        "password": "ValidPassword123",
        "full_name": "Rotation User",
    })
    assert reg.status_code == 201

    # 2. Login
    login = await client.post("/api/v1/auth/login", json={
        "email": "rotator@example.com",
        "password": "ValidPassword123",
    })
    assert login.status_code == 200
    refresh_cookie = login.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # 3. Refresh token rotation: exchange old refresh token for new one
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    new_refresh_cookie = refresh_res.cookies.get("refresh_token")
    assert new_refresh_cookie is not None
    assert new_refresh_cookie != refresh_cookie  # New token generated

    # 4. Replay attack: try using the old revoked refresh token
    client.cookies.set("refresh_token", refresh_cookie)
    replay_res = await client.post("/api/v1/auth/refresh")
    assert replay_res.status_code == 401
    assert "revoked" in replay_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_revokes_token(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "logout@example.com",
        "password": "ValidPassword123",
        "full_name": "Logout User",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "logout@example.com",
        "password": "ValidPassword123",
    })
    assert login.status_code == 200

    # Logout
    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200

    # Subsequent refresh must fail because token was revoked in DB
    refresh_attempt = await client.post("/api/v1/auth/refresh")
    assert refresh_attempt.status_code == 401


@pytest.mark.asyncio
async def test_invalid_bearer_token(client: AsyncClient):
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert res.status_code == 401
