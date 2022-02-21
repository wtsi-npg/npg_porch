import pytest
from sqlalchemy import select

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
        assert t.token is not None
        assert len(t.token) == 32
        assert t.date_issued is not None
        assert t.date_revoked is None
        assert t.pipeline.repository_uri == 'pipeline-test.com'
