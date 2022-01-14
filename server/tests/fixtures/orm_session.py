import pytest
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.ext.asyncio import AsyncSession

from npg.porchdb.models import Base


@pytest.fixture
def sync_session():
    'A synchronous sqlalchemy scoped session, connected to sqlite'

    sqlite_url = 'sqlite+pysqlite:///:memory:'

    engine = sqlalchemy.create_engine(sqlite_url, future=True)
    Base.metadata.schema = None
    Base.metadata.create_all(engine)
    SessionFactory = sqlalchemy.orm.sessionmaker(bind=engine)
    sess = sqlalchemy.orm.scoped_session(SessionFactory)
    yield sess
    sess.close()
    engine.dispose()


@pytest.fixture
def async_session():
    '''
    An asynchronous sqlalchemy session, connected to sqlite

    Requires an event loop and some awaiting to make it work
    '''

    sqlite_url = 'sqlite+aiosqlite:///:memory:'

    engine = sqlalchemy.create_async_engine(
        sqlite_url, future=True
    )
    Base.metadata.schema = None
    Base.metadata.create_all(engine)
    SesssionFactory = sqlalchemy.orm.sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    session = SesssionFactory()
    yield session
    session.close()
