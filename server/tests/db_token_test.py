import pytest
from sqlalchemy import select

from .fixtures.deploy_db import async_minimum
from npg.porchdb.models import Token

@pytest.mark.asyncio
async def test_token_creation(async_minimum):
    'Test token creation from a fixture'

    result = await async_minimum.execute(
        select(Token)
    )
    tokens = result.scalars().all()
    assert len(tokens) == 2
    for t in tokens:
        assert t.token != None
        assert len(t.token) == 32
        assert t.date_issued != None
        assert t.date_revoked == None
        assert t.pipeline.repository_uri == 'pipeline-test.com'
