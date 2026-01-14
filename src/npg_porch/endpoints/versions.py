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

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from starlette import status

from npg_porch.auth.token import validate
from npg_porch.db.connection import get_DbAccessor
from npg_porch.models.permission import Permission, PermissionValidationException
from npg_porch.models.version import Version

router = APIRouter(
    prefix="/versions",
    tags=["versions"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected error"},
    },
)


@router.get(
    "/{pipeline_name}",
    response_model=list[Version],
    summary="Get information about version of a pipeline.",
    description="Returns a list of pydantic Version models for a specific pipeline.",
)
async def get_versions(
    pipeline_name: str, db_accessor=Depends(get_DbAccessor)
) -> List[Version]:
    return await db_accessor.get_pipeline_versions(pipeline_name=pipeline_name)


@router.post(
    "/",
    response_model=Version,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Version was created"},
        status.HTTP_400_BAD_REQUEST: {
            "description": "Insufficient version properties provided"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Pipeline does not exist"},
        status.HTTP_409_CONFLICT: {
            "description": "Version already exists for this pipeline"
        },
    },
    summary="Create one version record.",
    description="""
    Using JSON data in the request, creates a new version record
    for an existing pipeline.
    A valid pipeline token is required for authorisation.
    """,
)
async def create_version(
    version: Version,
    db_accessor=Depends(get_DbAccessor),
    permission=Depends(validate),
) -> Version:
    try:
        permission.validate_pipeline(version.pipeline)
    except PermissionValidationException as e:
        logging.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Given credentials cannot be used for pipeline '{version.pipeline.name}'"
            ),
        )
    try:
        new_version = await db_accessor.create_version(version)
    except IntegrityError as e:
        logging.error(str(e))
        if "NOT NULL" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Version must specify a version and a complete pipeline",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Version already exists for this pipeline",
            )

    return new_version
