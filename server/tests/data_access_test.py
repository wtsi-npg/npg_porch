import pytest
from pydantic import ValidationError
from sqlalchemy.orm.exc import NoResultFound

from .fixtures.orm_session import async_session
from .fixtures.deploy_db import db_accessor
from npg.porchdb.data_access import AsyncDbAccessor
from npg.porch.models import Pipeline as ModelledPipeline, Task


def give_me_a_pipeline(number: int = 1):
    return ModelledPipeline(
        name=f'ptest {number}',
        version=str(number),
        uri=f'file:///team117/test_pipeline{number}'
    )


async def store_me_a_pipeline(dac: AsyncDbAccessor, number: int = 1) -> ModelledPipeline:
    return await dac.create_pipeline(give_me_a_pipeline(number))

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
    assert saved_task.pipeline.name == 'ptest 1'
    assert saved_task.task_input_id, 'Input ID is created automatically'

    events = await db_accessor.get_events_for_task(saved_task)
    assert len(events) == 1, 'An event was created with a successful task creation'
    assert events[0].change == 'Created', 'Message set'

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

    events = await db_accessor.get_events_for_task(tasks[0])
    assert len(events) == 2, 'Event for task creation, event for claiming'
    assert events[1].change == 'Task claimed'

    tasks = await db_accessor.claim_tasks(1, pipeline, 8)
    assert len(tasks) == 8, 'Lots of tasks claimed successfully'
    assert tasks[0].task_input == {'number': 2}, 'Tasks claimed sequentially'
    assert tasks[1].task_input == {'number': 3}, 'Tasks claimed sequentially'

    tasks = await db_accessor.claim_tasks(1, pipeline, 2)
    assert len(tasks) == 1, 'Cannot claim more tasks than are available'
    assert tasks[0].task_input == {'number': 10}, 'Last task is present'

@pytest.mark.asyncio
async def test_multi_claim_tasks(db_accessor):
    'Test to ensure no cross-talk between multiple pipelines and tasks'

    pipeline = await store_me_a_pipeline(db_accessor)
    other_pipeline = await store_me_a_pipeline(db_accessor, 2)

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={'number': i+1},
                pipeline=pipeline
            )
        )
        await db_accessor.create_task(
            token_id=2,
            task=Task(
                task_input={'number': i+1},
                pipeline=other_pipeline
            )
        )

    tasks = await db_accessor.claim_tasks(1, pipeline, 3)
    for i, t in enumerate(tasks, 1):
        assert t.pipeline == pipeline
        assert t.task_input == {'number': i}

    tasks = await db_accessor.claim_tasks(1, other_pipeline, 3)
    for i, t in enumerate(tasks, 1):
        assert t.pipeline == other_pipeline
        assert t.task_input == {'number': i}


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

    events = await db_accessor.get_events_for_task(modified_task)
    assert len(events) == 2, 'Task was created, and then updated'
    events[1].change == 'Task changed, new status DONE'

    # Try to change a task that doesn't exist
    with pytest.raises(NoResultFound):
        await db_accessor.update_task(1, Task(task_input={'number': None}, pipeline=saved_pipeline))

    # Try modifying something we're not allowed to
    saved_task.task_input_id = None
    with pytest.raises(Exception) as exception:
        await db_accessor.update_task(1, saved_task)
        assert exception.value == 'Cannot change task definition. Submit a new task instead'
