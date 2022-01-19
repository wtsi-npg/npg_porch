import pytest
import pytest_asyncio
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from npg.porchdb.models import Base


@pytest.fixture
def sync_session():
    'A synchronous sqlalchemy scoped session, connected to sqlite'

    sqlite_url = 'sqlite+pysqlite:///:memory:'

    engine = sqlalchemy.create_engine(sqlite_url, future=True)
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

    sqlite_url = 'sqlite+aiosqlite:///:memory:'

    engine = create_async_engine(
        sqlite_url, future=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SesssionFactory = sqlalchemy.orm.sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    session = SesssionFactory()
    yield session
    await session.close()
    await engine.dispose()
