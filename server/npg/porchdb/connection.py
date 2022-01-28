# Copyright (C) 2022 Genome Research Ltd.
#
# Author: Kieron Taylor kt19@sanger.ac.uk
# Author: Marina Gourtovaia mg8@sanger.ac.uk
#
# This file is part of npg_porch
#
# npg_porch is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.

import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from npg.porchdb.models import Base
from npg.porchdb.data_access import AsyncDbAccessor

config = {
    'DB_URL': os.environ.get('DB_URL'),
    'DB_SCHEMA': os.environ.get('DB_SCHEMA') if os.environ.get('DB_SCHEMA') else 'npg_porch',
    'TEST': os.environ.get('NPG_PORCH_MODE')
}

if config['TEST']:
    config['DB_URL'] = 'sqlite+aiosqlite:///:memory:'

if config['DB_URL'] is None or config['DB_URL'] == '':
    raise Exception("ENV['DB_URL'] must be set with a database URL")

engine = create_async_engine(
    config['DB_URL'], future=True
)
Base.metadata.schema = config['DB_SCHEMA']
session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def get_DbAccessor():
    'Provides a hook for fastapi to Depend on a DB session in each route'
    async with session_factory() as session:
        # Starting a transaction that finished automatically when the returned
        # object drops out of scope
        async with session.begin():
            yield AsyncDbAccessor(session)


async def deploy_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_engine():
    await engine.dispose()
