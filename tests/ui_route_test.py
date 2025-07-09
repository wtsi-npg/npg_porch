import pytest
from fastapi.testclient import TestClient

from npg_porch.endpoints import ui
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


@pytest.mark.asyncio
async def test_get_ui_pipeline_state_tasks(db_accessor):
    modelled_pipeline = Pipeline(
        name="test_pipeline", version="1.0", uri="file://test.pipeline"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    done_response = client.get(f"/ui/tasks/test_pipeline/{TaskStateEnum.DONE}")
    pending_response = client.get(f"/ui/tasks/test_pipeline/{TaskStateEnum.PENDING}")
    assert done_response.json()["recordsTotal"] == 0, "No tasks are done"
    assert pending_response.json()["recordsTotal"] == 3, "Three tasks are pending"

    # Change task to running
    await db_accessor.update_task(
        token_id=1,
        task=Task(
            task_input={"number": 1},
            pipeline=pipeline,
            status=TaskStateEnum.RUNNING,
        ),
    )

    # Change task to done
    await db_accessor.update_task(
        token_id=1,
        task=Task(
            task_input={"number": 2},
            pipeline=pipeline,
            status=TaskStateEnum.DONE,
        ),
    )

    done_response = client.get(f"/ui/tasks/test_pipeline/{TaskStateEnum.DONE}")
    pending_response = client.get(f"/ui/tasks/test_pipeline/{TaskStateEnum.PENDING}")
    not_done_response = client.get(f"/ui/tasks/test_pipeline/{ui.UiStateEnum.NOT_DONE}")
    all_response = client.get(f"/ui/tasks/test_pipeline/{ui.UiStateEnum.ALL}")
    assert done_response.json()["recordsTotal"] == 1, "One task is done"
    assert pending_response.json()["recordsTotal"] == 1, "One task is pending"
    assert not_done_response.json()["recordsTotal"] == 2, "Two tasks are not done"
    assert all_response.json()["recordsTotal"] == 3, "Three tasks are present"
