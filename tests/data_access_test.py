import re
import time

import pytest
from npg_porch.db.data_access import AsyncDbAccessor
from npg_porch.models import Pipeline as ModelledPipeline
from npg_porch.models import Task, TaskStateEnum
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound


def give_me_a_pipeline(number: int = 1):
    return ModelledPipeline(
        name=f"ptest {number}",
        version=str(number),
        uri=f"file:///team117/test_pipeline{number}",
    )


async def store_me_a_pipeline(
    dac: AsyncDbAccessor, number: int = 1
) -> ModelledPipeline:
    return await dac.create_pipeline(give_me_a_pipeline(number))


def test_data_accessor_setup(async_session):
    with pytest.raises(TypeError):
        dac = AsyncDbAccessor()

    dac = AsyncDbAccessor(async_session)
    assert dac


@pytest.mark.asyncio
async def test_get_pipeline(db_accessor):
    with pytest.raises(TypeError):
        db_accessor.get_pipeline_by_name()

    with pytest.raises(NoResultFound):
        await db_accessor.get_pipeline_by_name("not here")

    pipeline = await db_accessor.get_pipeline_by_name("ptest one")
    assert pipeline
    assert pipeline.name == "ptest one"
    assert pipeline.version == "0.3.14"


@pytest.mark.asyncio
async def test_get_all_pipelines(db_accessor):
    pipes = await db_accessor.get_all_pipelines()
    assert isinstance(pipes, list)
    assert len(pipes) == 1

    assert pipes[0].name == "ptest one"

    # Make a second pipeline with the same version and different uri as the one in the fixture
    await db_accessor.create_pipeline(
        ModelledPipeline(
            name="ptest two", version="0.3.14", uri="test-the-other-one.com"
        )
    )

    pipes = await db_accessor.get_all_pipelines(version="0.3.14")
    assert len(pipes) == 2

    pipes = await db_accessor.get_all_pipelines(uri="test-the-other-one.com")
    assert len(pipes) == 1

    pipes = await db_accessor.get_all_pipelines(
        version="0.3.14", uri="pipeline-test.com"
    )
    assert (
        len(pipes) == 1
    ), "Both parameters work together, even if it does not reduce the results"


@pytest.mark.asyncio
async def test_create_pipeline(db_accessor):
    pipeline = give_me_a_pipeline()

    saved_pipeline = await db_accessor.create_pipeline(pipeline)

    assert isinstance(saved_pipeline, ModelledPipeline)
    assert saved_pipeline.name == pipeline.name
    assert saved_pipeline.version == pipeline.version
    assert saved_pipeline.uri == pipeline.uri

    with pytest.raises(AssertionError):
        await db_accessor.create_pipeline({})
    with pytest.raises(IntegrityError) as exception:
        # Making duplicate provides a useful error
        await db_accessor.create_pipeline(pipeline)

        assert re.match("UNIQUE constraint failed", exception.value)


@pytest.mark.asyncio
async def test_create_task(db_accessor):
    # create task with no pipeline
    with pytest.raises(ValidationError):
        await db_accessor.create_task(token_id=1, task=Task(task_input={"test": True}))

    saved_pipeline = await store_me_a_pipeline(db_accessor)

    task = Task(
        pipeline=saved_pipeline, task_input={"test": True}, status=TaskStateEnum.PENDING
    )

    (saved_task, created) = await db_accessor.create_task(token_id=1, task=task)
    assert created is True
    assert (
        saved_task.status == TaskStateEnum.PENDING
    ), "State automatically set to PENDING"
    assert saved_task.pipeline.name == "ptest 1"
    assert saved_task.task_input_id, "Input ID is created automatically"

    events = await db_accessor.get_events_for_task(saved_task)
    assert len(events) == 1, "An event was created with a successful task creation"
    assert events[0].change == "Created", "Message set"

    (existing_task, created) = await db_accessor.create_task(1, task)
    assert created is False
    assert (
        existing_task.status == TaskStateEnum.PENDING
    ), "State automatically set to PENDING"
    assert existing_task.pipeline.name == "ptest 1"
    events = await db_accessor.get_events_for_task(existing_task)
    assert len(events) == 1, "No additional events"


@pytest.mark.asyncio
async def test_claim_tasks(db_accessor):
    # Claim on a missing pipeline
    pipeline = give_me_a_pipeline()

    with pytest.raises(NoResultFound) as exception:
        await db_accessor.claim_tasks(1, pipeline)

        assert exception.value == "Pipeline not found"

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
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    tasks = await db_accessor.claim_tasks(1, pipeline)
    assert len(tasks) == 1, "One task claimed successfully"
    assert tasks[0].status == TaskStateEnum.CLAIMED
    assert tasks[0].task_input == {"number": 1}
    assert tasks[0].task_input_id, "unique ID set"

    events = await db_accessor.get_events_for_task(tasks[0])
    assert len(events) == 2, "Event for task creation, event for claiming"
    assert events[1].change == "Task claimed"

    tasks = await db_accessor.claim_tasks(1, pipeline, 8)
    assert len(tasks) == 8, "Lots of tasks claimed successfully"
    assert tasks[0].task_input == {"number": 2}, "Tasks claimed sequentially"
    assert tasks[1].task_input == {"number": 3}, "Tasks claimed sequentially"

    tasks = await db_accessor.claim_tasks(1, pipeline, 2)
    assert len(tasks) == 1, "Cannot claim more tasks than are available"
    assert tasks[0].task_input == {"number": 10}, "Last task is present"


@pytest.mark.asyncio
async def test_multi_claim_tasks(db_accessor):
    "Test to ensure no cross-talk between multiple pipelines and tasks"

    pipeline = await store_me_a_pipeline(db_accessor)
    other_pipeline = await store_me_a_pipeline(db_accessor, 2)

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )
        await db_accessor.create_task(
            token_id=2,
            task=Task(
                task_input={"number": i + 1},
                pipeline=other_pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    tasks = await db_accessor.claim_tasks(1, pipeline, 3)
    for i, t in enumerate(tasks, 1):
        assert t.pipeline == pipeline
        assert t.task_input == {"number": i}

    tasks = await db_accessor.claim_tasks(1, other_pipeline, 3)
    for i, t in enumerate(tasks, 1):
        assert t.pipeline == other_pipeline
        assert t.task_input == {"number": i}


@pytest.mark.asyncio
async def test_update_tasks(db_accessor):
    saved_pipeline = await store_me_a_pipeline(db_accessor)
    (saved_task, created) = await db_accessor.create_task(
        token_id=1,
        task=Task(
            task_input={"number": 1},
            pipeline=saved_pipeline,
            status=TaskStateEnum.PENDING,
        ),
    )

    saved_task.status = TaskStateEnum.DONE
    modified_task = await db_accessor.update_task(1, saved_task)

    assert modified_task == saved_task

    events = await db_accessor.get_events_for_task(modified_task)
    assert len(events) == 2, "Task was created, and then updated"
    assert events[1].change == f"Task changed, new status {TaskStateEnum.DONE}"

    # Try to change a task that doesn't exist
    with pytest.raises(NoResultFound):
        await db_accessor.update_task(
            1,
            Task(
                task_input={"number": None},
                pipeline=saved_pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    # Try modifying something we're not allowed to
    saved_task.task_input_id = None
    with pytest.raises(Exception) as exception:
        await db_accessor.update_task(1, saved_task)
        assert (
            exception.value
            == "Cannot change task definition. Submit a new task instead"
        )


@pytest.mark.asyncio
async def test_get_tasks(db_accessor):
    all_tasks = await db_accessor.get_tasks()

    assert (
        len(all_tasks) == 2
    ), "All tasks currently includes two for one pipeline from the fixture"

    tasks = await db_accessor.get_tasks(pipeline_name="ptest one")

    assert tasks == all_tasks, "Filtering by pipeline name gives the same result"

    tasks = await db_accessor.get_tasks(task_status=TaskStateEnum.FAILED)
    assert len(tasks) == 0, "No failed tasks yet"

    # Create an additional pipeline and tasks

    pipeline = await store_me_a_pipeline(db_accessor, 2)

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    all_tasks = await db_accessor.get_tasks()
    assert len(all_tasks) == 5, "Now we have five tasks in two pipelines"

    tasks = await db_accessor.get_tasks(pipeline_name="ptest one")
    assert len(tasks) == 2, "New tasks filtered out by pipeline name"
    assert tasks[0].pipeline.name == "ptest one"

    # Change one task to another status
    await db_accessor.update_task(
        token_id=1,
        task=Task(
            task_input={"number": 3}, pipeline=pipeline, status=TaskStateEnum.DONE
        ),
    )

    tasks = await db_accessor.get_tasks(task_status=TaskStateEnum.DONE)
    assert len(tasks) == 1, "Not done tasks are filtered"
    assert tasks[0].task_input == {"number": 3}, "Leaving only one"

    # Check interaction of both constraints

    tasks = await db_accessor.get_tasks(
        pipeline_name="ptest one", task_status=TaskStateEnum.DONE
    )
    assert len(tasks) == 0, 'Pipeline "ptest one" has no DONE tasks'


@pytest.mark.asyncio
async def test_get_expanded_tasks(db_accessor):
    expanded_tasks = await db_accessor.get_expanded_tasks()

    assert len(expanded_tasks) == 2, "Gets all tasks"

    pipeline = await store_me_a_pipeline(db_accessor)

    for i in range(3):
        await db_accessor.create_task(
            token_id=1,
            task=Task(
                task_input={"number": i + 1},
                pipeline=pipeline,
                status=TaskStateEnum.PENDING,
            ),
        )

    expanded_tasks = await db_accessor.get_expanded_tasks()

    assert len(expanded_tasks) == 5, "Gets tasks from new pipeline as well"
    assert (
        expanded_tasks[0].created == expanded_tasks[0].updated
    ), "Creation date is the same as status update date"

    expanded_tasks = await db_accessor.get_expanded_tasks(pipeline.name)

    assert (
        len(expanded_tasks) == 3
    ), "Gets only tasks from the pipeline that is specified"

    time.sleep(1)  # Delay to ensure a difference in time stamp

    # Change one task to another status
    await db_accessor.update_task(
        token_id=1,
        task=Task(
            task_input={"number": 1}, pipeline=pipeline, status=TaskStateEnum.DONE
        ),
    )

    expanded_tasks = await db_accessor.get_expanded_tasks()

    assert len(expanded_tasks) == 5, "Updating a task does not change number of results"
    # ordered by updated date, so this should always be the task that was updated
    assert (
        expanded_tasks[0].created < expanded_tasks[0].updated
    ), "Status update date is more recent than creation date"


@pytest.mark.asyncio
async def test_count_tasks(db_accessor, async_tasks):
    task_count = await db_accessor.count_tasks()

    assert task_count == 12, "Tasks are counted correctly"
