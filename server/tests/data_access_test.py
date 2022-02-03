from typing import Sequence
import pytest
from pydantic import ValidationError
from sqlalchemy.orm.exc import NoResultFound

from .fixtures.orm_session import async_session
from .fixtures.deploy_db import db_accessor
from npg.porchdb.data_access import AsyncDbAccessor
from npg.porch.models import Pipeline as ModelledPipeline, Task


def give_me_a_pipeline():
    return ModelledPipeline(
        name='ptest two',
        version='2',
        uri='file:///team117/test_pipeline'
    )

async def store_me_a_pipeline(dac: AsyncDbAccessor) -> ModelledPipeline:
    return await dac.create_pipeline(give_me_a_pipeline())

@pytest.mark.asyncio
def test_data_accessor_setup(async_session):
    with pytest.raises(TypeError):
        dac = AsyncDbAccessor()

    dac = AsyncDbAccessor(async_session)
    assert dac

@pytest.mark.asyncio
async def test_get_pipeline(db_accessor):
    with pytest.raises(TypeError):
        db_accessor.get_pipeline()

    with pytest.raises(NoResultFound):
        await db_accessor.get_pipeline('not here')

    pipeline = await db_accessor.get_pipeline('ptest one')
    assert pipeline.name == 'ptest one'
    assert pipeline.version == '0.3.14'

@pytest.mark.asyncio
async def test_get_all_pipelines(db_accessor):
    pipes = await db_accessor.get_all_pipelines()
    assert isinstance(pipes, list)
    assert len(pipes) == 1

    assert pipes[0].name == 'ptest one'

@pytest.mark.asyncio
async def test_create_pipeline(db_accessor):
    pipeline = give_me_a_pipeline()

    saved_pipeline = await db_accessor.create_pipeline(pipeline)

    assert isinstance(saved_pipeline, ModelledPipeline)
    assert saved_pipeline.name == pipeline.name
    assert saved_pipeline.version == pipeline.version
    assert saved_pipeline.uri == pipeline.uri

    with pytest.raises(AssertionError):
        saved_pipeline = await db_accessor.create_pipeline({})

@pytest.mark.asyncio
async def test_create_task(db_accessor):
    # create task with no pipeline
    with pytest.raises(ValidationError):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={'test': True}
            )
        )

    saved_pipeline = await store_me_a_pipeline(db_accessor)

    task = Task(
        pipeline=saved_pipeline,
        task_input={'test': True}
    )

    saved_task = await db_accessor.create_task(
        token_id=1,
        task=task
    )

    assert saved_task.status == 'PENDING', 'State automatically set to PENDING'
    assert saved_task.pipeline.name == 'ptest two'
    assert saved_task.task_input_id, 'Input ID is created automatically'

@pytest.mark.asyncio
async def test_claim_tasks(db_accessor):
    # Claim on a missing pipeline
    pipeline = give_me_a_pipeline()

    with pytest.raises(NoResultFound) as exception:
        tasks = await db_accessor.claim_tasks(1, pipeline)

        assert exception.value == 'Pipeline not found'

    # Now try again with a pipeline but no tasks
    await db_accessor.create_pipeline(pipeline)
    tasks = await db_accessor.claim_tasks(1, pipeline)
    assert isinstance(tasks, list)
    assert len(tasks) == 0

    # Again, this time with valid tasks
    for i in range(10):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={'number': i+1},
                pipeline=pipeline
            )
        )

    tasks = await db_accessor.claim_tasks(1, pipeline)
    assert len(tasks) == 1, 'One task claimed successfully'
    assert tasks[0].status == 'CLAIMED'
    assert tasks[0].task_input == {'number': 1}
    assert tasks[0].task_input_id, 'unique ID set'

    tasks = await db_accessor.claim_tasks(1, pipeline, 8)
    assert len(tasks) == 8, 'Lots of tasks claimed successfully'
    assert tasks[0].task_input == {'number': 2}, 'Tasks claimed sequentially'
    assert tasks[1].task_input == {'number': 3}, 'Tasks claimed sequentially'

    tasks = await db_accessor.claim_tasks(1, pipeline, 2)
    assert len(tasks) == 1, 'Cannot claim more tasks than are available'
    assert tasks[0].task_input == {'number': 10}, 'Last task is present'

    # Test to ensure no cross-talk between multiple pipelines and tasks?
    # Test that claim events were set?

@pytest.mark.asyncio
async def test_update_tasks(db_accessor):
    saved_pipeline = await store_me_a_pipeline(db_accessor)
    saved_task = await db_accessor.create_task(
        token_id=1,
        task=Task(
            task_input={'number': 1},
            pipeline=saved_pipeline
        )
    )

    saved_task.status = 'DONE'
    modified_task = await db_accessor.update_task(1, saved_task)

    assert modified_task == saved_task

    # Try to change a task that doesn't exist
    with pytest.raises(NoResultFound):
        await db_accessor.update_task(1, Task(task_input={'number': None}, pipeline=saved_pipeline))

    # Try modifying something we're not allowed to
    saved_task.task_input_id = None
    with pytest.raises(Exception) as exception:
        await db_accessor.update_task(1, saved_task)
        assert exception.value == 'Cannot change task definition. Submit a new task instead'
