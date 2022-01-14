from sqlalchemy import select

from .fixtures.deploy_db import minimum_data
from npg.porchdb.models import Pipeline


def test_fixture(minimum_data):
    'Proving a point about fixtures and synchronous usage of ORM'

    pipes = minimum_data.execute(
        select(Pipeline)
    ).scalars().all()

    assert len(pipes) == 1
    assert pipes[0].repository_uri == 'pipeline-test.com'
