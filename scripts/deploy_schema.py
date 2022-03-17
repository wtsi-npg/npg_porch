# Replace with Alembic in due course

import os
import sqlalchemy

import npg.porchdb.models

db_url = os.environ.get('DB_URL')
schema_name = os.environ.get('DB_SCHEMA')
if schema_name is None:
    schema_name = 'npg_porch'

engine = sqlalchemy.create_engine(db_url)

npg.porchdb.models.Base.metadata.schema = schema_name
npg.porchdb.models.Base.metadata.create_all(engine)
