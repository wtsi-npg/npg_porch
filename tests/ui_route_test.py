from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from npg_porch.endpoints import ui
from npg_porch.server import app
from npg_porch.models import Pipeline, Task, TaskStateEnum

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_ui_tasks(db_accessor, async_past_tasks):
    done_response = client.get(f"/ui/tasks/All/{TaskStateEnum.DONE}/{datetime.min}")
    pending_response = client.get(
        f"/ui/tasks/All/{TaskStateEnum.PENDING}/{datetime.min}"
    )
    not_done_response = client.get(
        f"/ui/tasks/All/{ui.UiStateEnum.NOT_DONE}/{datetime.min}"
    )
    all_response = client.get(f"/ui/tasks/All/{ui.UiStateEnum.ALL}/{datetime.min}")

    # These include async minimum tasks as well
    assert done_response.json()["recordsTotal"] == 3, "Three tasks are done"
    assert pending_response.json()["recordsTotal"] == 5, "Three tasks are pending"
    assert not_done_response.json()["recordsTotal"] == 11, "Nine tasks are not done"
    assert all_response.json()["recordsTotal"] == 14, "Twelve tasks are present"

    recent_fail_response = client.get(
        f"/ui/tasks/All/{TaskStateEnum.FAILED}/{datetime.now() - timedelta(days=14)}"
    )

    assert (
        recent_fail_response.json()["recordsTotal"] == 2
    ), "Two tasks have failed within the last 14 days"

    modelled_pipeline = Pipeline(
        name="new_pipeline", version="1.0", uri="file://test.pipeline"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    response = client.get(f"/ui/tasks/new_pipeline/{ui.UiStateEnum.ALL}/{datetime.min}")
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

    done_response = client.get(
        f"/ui/tasks/new_pipeline/{TaskStateEnum.DONE}/{datetime.min}"
    )
    pending_response = client.get(
        f"/ui/tasks/new_pipeline/{TaskStateEnum.PENDING}/{datetime.min}"
    )
    assert (
        done_response.json()["recordsTotal"] == 0
    ), "No tasks are done in new pipeline after task creation"
    assert (
        pending_response.json()["recordsTotal"] == 3
    ), "Three tasks are pending in new pipeline after task creation"


@pytest.mark.asyncio
async def test_get_long_running_ui_tasks(db_accessor):
    modelled_pipeline = Pipeline(
        name="test_pipeline", version="1.0", uri="file://test.pipeline"
    )
    pipeline = await db_accessor.create_pipeline(modelled_pipeline)

    for i in range(4):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    for i in range(2):
        await db_accessor.update_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.DONE,
            ),
        )

    response = client.get("/ui/long_running")

    assert response.json()["recordsTotal"] == 2, "Two long running tasks"
