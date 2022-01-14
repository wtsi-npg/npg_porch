import pytest
from sqlalchemy import select

from .fixtures.deploy_db import sync_minimum, async_minimum
from npg.porchdb.models import Pipeline


def test_fixture(sync_minimum):
    'Proving a point about fixtures and synchronous usage of ORM'

    pipes = sync_minimum.execute(
        select(Pipeline)
    ).scalars().all()

    assert len(pipes) == 1
    assert pipes[0].repository_uri == 'pipeline-test.com'

@pytest.mark.asyncio
async def test_async_fixture(async_minimum):
    'Test an async session with a trivial ORM operation'

    result = await async_minimum.execute(
        select(Pipeline)
    )

    pipes = result.scalars().all()
    assert len(pipes) == 1
    assert pipes[0].repository_uri == 'pipeline-test.com'
