# Replace with Alembic in due course

import os
import sqlalchemy

import npg_porch.db.models

db_url = os.environ.get('DB_URL')
schema_name = os.environ.get('DB_SCHEMA')
if schema_name is None:
    schema_name = 'npg_porch'

print(f'Deploying npg_porch tables to schema {schema_name}')

engine = sqlalchemy.create_engine(
    db_url,
    connect_args={'options': f'-csearch_path={schema_name}'}
)

npg_porch.db.models.Base.metadata.schema = schema_name
npg_porch.db.models.Base.metadata.create_all(engine)
