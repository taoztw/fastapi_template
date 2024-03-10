import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_hospital_info(async_client: AsyncClient):
    response = await async_client.get("/simple/index")
    print("response", response.text)
    assert response.status_code == 200
