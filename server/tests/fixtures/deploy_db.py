from collections import UserList
import pytest
import pytest_asyncio

from .orm_session import sync_session, async_session
from npg.porchdb.models import (
    Pipeline, Task, Event, Agent
)

@pytest.fixture
def minimum_data():
    'Provides one of everything'

    pipeline = Pipeline(
        repository_uri='pipeline-test.com',
        version='0.3.14'
    )
    job_finder = Agent(
        name='job_finder'
    )
    job_runner = Agent(
        name='job_runner'
    )
    b_event = a_event = Event(
        agent=job_finder,
        change='Created'
    )
    tasks = [
        Task(
            pipeline=pipeline,
            events=[a_event],
            job_descriptor='aaaaaaaaa',
            definition={
                'to_do': 'stuff',
                'why': 'reasons'
            }
        ),
        Task(
            pipeline=pipeline,
            events=[b_event],
            job_descriptor='bbbbbbbbb',
            definition={
                'to_do': 'stuff',
                'why': 'reasons'
            }
        )
    ]
    entities = UserList([pipeline, job_finder, job_runner, b_event, a_event])
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
