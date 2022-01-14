import pytest

from .orm_session import sync_session
from npg.porchdb.models import (
    Pipeline, Task, Event, Agent
)

@pytest.fixture
def minimum_data(sync_session):
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

    sync_session.add_all([pipeline, job_finder, job_runner])
    sync_session.add_all(tasks)
    sync_session.commit()
    return sync_session
