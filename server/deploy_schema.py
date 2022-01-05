# Replace with Alembic in due course

import os
import sqlalchemy

import npg.porchdb.models

db_url = os.environ.get('DB_URL')

engine = sqlalchemy.create_engine(db_url)

npg.porchdb.models.Base.metadata.create_all(engine)
