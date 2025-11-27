# Copyright (C) 2025 Genome Research Ltd.
#
# Author: Michael Kubiak mk35@sanger.ac.uk
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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm.exc import NoResultFound
from starlette import status

from npg_porch.db.connection import get_DbAccessor
from npg_porch.models.pipeline import Pipeline

router = APIRouter(
    prefix="/versions",
    tags=["versions"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected error"},
    },
)


@router.get(
    "/{pipeline}",
    response_model=list[str],
    summary="Get information about version of a pipeline.",
    description="Returns a list of pydantic Version models for a specific pipeline.",
)
async def get_versions(
    pipeline_name: str, db_accessor=Depends(get_DbAccessor)
) -> list[Pipeline]:
    versions = None
    try:
        versions = await db_accessor.get_pipeline_versions(pipeline_name=pipeline_name)
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail=f"Pipeline '{pipeline_name}' not _found"
        )
    return versions
