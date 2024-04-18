import os
import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.orm

from npg_porch.db.models import Base
from npg_porch.db.connection import session_factory, deploy_schema, close_engine


@pytest.fixture
def sync_session():
    '''
    A synchronous sqlalchemy scoped session, connected to sqlite
    Use for tests that don't need a running npg_porch server
    '''

    sqlite_url = 'sqlite+pysqlite:///:memory:'
    engine = sqlalchemy.create_engine(sqlite_url)
    Base.metadata.create_all(engine)
    SessionFactory = sqlalchemy.orm.sessionmaker(bind=engine)
    sess = sqlalchemy.orm.scoped_session(SessionFactory)
    yield sess
    sess.close()
    engine.dispose()


@pytest_asyncio.fixture
async def async_session():
    '''
    An asynchronous sqlalchemy session, connected to sqlite

    Requires an event loop and some awaiting to make it work, e.g.
    ```
    @pytest.mark.asyncio
    async def test(async_session):
        with async_session.begin() as session:
            await session.execute('SQL')
        ...
    ```
    '''
    if os.environ.get('NPG_PORCH_MODE') is None:
        raise Exception('Do not run async tests without setting $ENV{NPG_PORCH_MODE}')
    await deploy_schema()
    session = session_factory()

    yield session
    await session.close()
    await close_engine()
