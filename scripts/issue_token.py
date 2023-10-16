#!/usr/bin/env python

import argparse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from npg.porchdb.models import Token, Pipeline

parser = argparse.ArgumentParser(
    description='Creates a token in the backend DB and returns it'
)

parser.add_argument(
    '-H', '--host', help='Postgres host', required=True
)
parser.add_argument(
    '-d', '--database', help='Postgres database', default='npg_porch'
)
parser.add_argument(
    '-s', '--schema', help='Postgres schema', default='npg_porch'
)
parser.add_argument(
    '-u', '--user', help='Postgres rw user', required=True
)
parser.add_argument(
    '-p', '--password', help='Postgres rw password', required=True
)
parser.add_argument(
    '-P', '--port', help='Postgres port', required=True
)
parser.add_argument(
    '-n', '--pipeline', help='Pipeline name. If given, create '
)
parser.add_argument(
    '-D', '--description', help='Description of token purpose', required=True
)

args = parser.parse_args()


db_url = f'postgresql+psycopg2://{args.user}:{args.password}@{args.host}:{args.port}/{args.database}'

engine = create_engine(db_url, connect_args={'options': f'-csearch_path={args.schema}'})
SessionFactory = sessionmaker(bind=engine)
session = SessionFactory()

token = None
pipeline = None

if args.pipeline:
    try:
        pipeline = session.execute(
            select(Pipeline)
            .where(Pipeline.name == args.pipeline)
        ).scalar_one()
    except NoResultFound:
        raise Exception(
            'Pipeline with name {} not found in database'.format(args.pipeline)
        )

    token = Token(
        pipeline=pipeline,
        description=args.description
    )
else:
    token = Token(description=args.description)

session.add(token)
session.commit()

print(token.token)

session.close()
engine.dispose()
