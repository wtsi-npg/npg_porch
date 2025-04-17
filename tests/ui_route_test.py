import pytest
from fastapi.testclient import TestClient
from npg_porch.server import app
from npg_porch.models import Pipeline, Task, TaskStateEnum

client = TestClient(app)


def test_get_ui_tasks(async_minimum):
    response = client.get("/ui/tasks")
    assert response.status_code == 200
    assert response.json()["recordsTotal"] == 2


@pytest.mark.asyncio
async def test_get_ui_pipeline_tasks(db_accessor):
    modelled_pipeline = Pipeline(
        name="test_pipeline", version="1.0", uri="file://test.pipeline"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    response = client.get("/ui/tasks/test_pipeline")
    assert response.json()["recordsTotal"] == 0, "No tasks in new pipeline"

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )
    response = client.get("/ui/tasks/test_pipeline")
    assert (
        response.json()["recordsTotal"] == 3
    ), "Only tasks added to pipeline appear in response"
