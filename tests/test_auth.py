import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_agent(client: AsyncClient):
    """Test registering a support agent and logging in to receive JWT token."""
    # 1. Register agent
    register_payload = {
        "email": "testagent@support.com",
        "password": "Password123!",
        "full_name": "Test Support Agent"
    }
    reg_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "testagent@support.com"

    # 2. Login agent
    login_payload = {
        "email": "testagent@support.com",
        "password": "Password123!"
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 3. Test /me endpoint
    headers = {"Authorization": f"Bearer {token}"}
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["email"] == "testagent@support.com"
