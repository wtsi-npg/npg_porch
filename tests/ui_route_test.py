from fastapi.testclient import TestClient
from npg_porch.server import app
from npg_porch.models import TaskExpanded

client = TestClient(app)


def test_get_ui_tasks(async_minimum):
    response = client.get("/ui/tasks")
    assert response.status_code == 200
    assert response.json()["recordsTotal"] == 2
