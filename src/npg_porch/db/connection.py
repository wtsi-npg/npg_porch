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

from npg_porch.db.models import Base
from npg_porch.db.data_access import AsyncDbAccessor
from npg_porch.db.auth import Validator

config = {
    "DB_URL": os.environ.get("DB_URL"),
    "DB_SCHEMA": os.environ.get("DB_SCHEMA")
    if os.environ.get("DB_SCHEMA")
    else "npg_porch",
    "TEST": os.environ.get("NPG_PORCH_MODE"),
}

if config["TEST"]:
    config["DB_URL"] = "sqlite+aiosqlite:///:memory:"

if config["DB_URL"] is None or config["DB_URL"] == "":
    raise Exception(
        "ENV['DB_URL'] must be set with a database URL, or NPG_PORCH_MODE must be set for testing"
    )


# asyncpg driver receives options differently to psycopg
# Embed them inside a server_settings dict
connect_args = {}
if config["TEST"] is None:
    connect_args = {
        "server_settings": {"options": "-csearch_path={}".format(config["DB_SCHEMA"])}
    }
engine = create_async_engine(
    config["DB_URL"], connect_args=connect_args, pool_pre_ping=True
)
Base.metadata.schema = config["DB_SCHEMA"]
session_factory = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_DbAccessor():
    """
    Provides a hook for fastapi to Depend on a DB session in each route.

    Yields an instance of AsyncDbAccessor class, which provides an API
    for access to data.

    Starts a transaction that finished automatically when the returned
    object drops out of scope.
    """
    async with session_factory() as session:
        async with session.begin():
            yield AsyncDbAccessor(session)


async def get_CredentialsValidator():
    """
    Similar to get_DbAccessor, but yields an instance of the Validator class,
    which provides methods for validating credentials submitted with the
    request.
    """
    async with session_factory() as session:
        async with session.begin():
            yield Validator(session)


async def deploy_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine():
    "Currently only needed when testing to force fixtures to refresh"
    await engine.dispose()
