from collections import UserList
import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from npg_porch.db.models import Pipeline, Task, Event, Token
from npg_porch.db.data_access import AsyncDbAccessor
from npg_porch.models import Task as ModelledTask, TaskStateEnum
from npg_porch.server import app


@pytest.fixture
def minimum_data():
    "Provides one or two of everything"

    pipeline = Pipeline(
        name="ptest one", repository_uri="pipeline-test.com", version="0.3.14"
    )
    tokens = [
        Token(
            token="cac0533d5599489d9a3d998028a79fe8",
            pipeline=pipeline,
            description="OpenStack host, job finder",
        ),
        Token(pipeline=pipeline, description="Seqfarm host, job runner"),
        Token(
            token="4bab73544c834c6f86f9662e5de26d0d", description="Seqfarm host, admin"
        ),
    ]
    #  Initialising these events as the same object was causing confusion in the database
    a_event = Event(token=tokens[0], change="Created")
    b_event = Event(token=tokens[0], change="Created")
    tasks = [
        Task(
            pipeline=pipeline,
            events=[a_event],
            job_descriptor="8cb72a9439dc643d67e859ceca424b9327a9c1abf9c772525df299f656137c22",
            definition={"to_do": "stuff", "why": "reasons"},
            state=TaskStateEnum.PENDING,
        ),
        Task(
            pipeline=pipeline,
            events=[b_event],
            # Probably wrong job_descriptor
            job_descriptor="4994ef1668bc9614bf0a8f199da50345e85e8b714ab91e95cf619c74af7d3eda",
            definition={"to_do": "more stuff", "why": "reasons"},
            state=TaskStateEnum.PENDING,
        ),
    ]

    entities = UserList([pipeline, b_event, a_event])
    entities.extend(tokens)
    entities.extend(tasks)

    return entities


@pytest.fixture
def lots_of_tasks():
    "A good supply of tasks for testing claims"

    pipeline = Pipeline(
        name="ptest some", repository_uri="pipeline-test.com", version="0.3.14"
    )
    job_finder_token = Token(
        token="ba53eaf7073d4c2b95ca47aeed41086c",
        pipeline=pipeline,
        description="OpenStack host, job finder",
    )

    tasks = []
    for i in range(0, 10):
        # A convoluted way of running generate_task_id() so we can set it
        # correctly in the DB without going through the API
        t = ModelledTask(
            pipeline={"name": "does not matter"},
            task_input={"input": i + 1},
            status=TaskStateEnum.PENDING,
        )
        t_db = Task(
            pipeline=pipeline,
            job_descriptor=t.generate_task_id(),
            state=t.status,
            definition=t.task_input,
        )
        tasks.append(t_db)

    entities = UserList([pipeline, job_finder_token])
    for t in tasks:
        entities.append(t)
    return entities


@pytest.fixture
def sync_minimum(sync_session, minimum_data):
    sync_session.add_all(minimum_data)
    sync_session.commit()
    return sync_session


@pytest_asyncio.fixture
async def async_minimum(async_session, minimum_data):
    async_session.add_all(minimum_data)
    await async_session.commit()
    return async_session


@pytest_asyncio.fixture
async def async_tasks(async_session, lots_of_tasks):
    async_session.add_all(lots_of_tasks)
    await async_session.commit()
    return async_session


@pytest_asyncio.fixture()
async def fastapi_testclient(async_session) -> TestClient:
    """
    Provides an uvicorn TestClient wrapping the application

    No data: Combine with another fixture to have test data, e.g.
    `def my_test(data_fixture, fastapi_testclient)`
    """
    async with async_session.begin():
        yield TestClient(app)


@pytest_asyncio.fixture()
async def db_accessor(async_minimum):
    """
    Provides an instance of AsyncDbAccessor with a live session
    and data provided by the minimum_data fixture
    """
    yield AsyncDbAccessor(async_minimum)
