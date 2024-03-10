from fastapi.testclient import TestClient


def test_index(client: TestClient):
    res = client.get("/simple/index")
    assert res.status_code == 200
