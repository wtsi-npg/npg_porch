import pytest
from sqlalchemy import select

from .fixtures.deploy_db import async_minimum
from npg.porchdb.models import Task

@pytest.mark.asyncio
async def test_task_creation(async_minimum):
    ''''
    Test task creation from a fixture.
    Relationships test.
    '''

    result = await async_minimum.execute(
        select(Task)
    )
    tasks = result.scalars().all()
    assert len(tasks) == 2
    task_a = tasks[0]
    assert task_a.job_descriptor == '8cb72a9439dc643d67e859ceca424b9327a9c1abf9c772525df299f656137c22'
    assert task_a.pipeline.repository_uri == 'pipeline-test.com'
    events = task_a.events
    assert len(events) == 1
    assert events[0].change == 'Created'
    assert events[0].token is not None

