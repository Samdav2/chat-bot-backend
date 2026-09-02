import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quick_responses_crud(client: AsyncClient):
    """Test full CRUD operations for Quick Responses endpoint."""
    # 1. Register & login agent
    reg_payload = {
        "email": "snippetagent@support.com",
        "password": "Password123!",
        "full_name": "Snippet Agent",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "snippetagent@support.com", "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List initial quick responses (empty)
    list_resp = await client.get("/api/v1/quick-responses", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["success"] is True

    # 3. Create a quick response
    create_payload = {
        "title": "OTP Delay Guidance",
        "content": "Codes usually arrive within 1-3 minutes. If code does not arrive, click Cancel for an instant refund.",
    }
    create_resp = await client.post("/api/v1/quick-responses", json=create_payload, headers=headers)
    assert create_resp.status_code == 200
    created_data = create_resp.json()["data"]
    snippet_id = created_data["id"]
    assert created_data["title"] == "OTP Delay Guidance"

    # 4. List again and verify item is present
    list_resp2 = await client.get("/api/v1/quick-responses", headers=headers)
    assert len(list_resp2.json()["data"]) >= 1

    # 5. Delete quick response
    del_resp = await client.delete(f"/api/v1/quick-responses/{snippet_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["id"] == snippet_id
