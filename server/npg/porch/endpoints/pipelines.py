# Copyright (C) 2021, 2022 Genome Research Ltd.
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

from fastapi import APIRouter, HTTPException, Depends
import logging
from typing import List, Optional
import re
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from starlette import status

from npg.porch.models.pipeline import Pipeline
from npg.porchdb.connection import get_DbAccessor

router = APIRouter(
    prefix="/pipelines",
    tags=["pipelines"]
)

@router.get(
    "/",
    response_model=List[Pipeline],
    summary="Get information about all pipelines.",
    description="Get all pipelines as a list. A uri and/or version filter can be used."
)
async def get_pipelines(
    uri: Optional[str] = None,
    version: Optional[str] = None,
    db_accessor=Depends(get_DbAccessor)
) -> List[Pipeline]:
    return await db_accessor.get_all_pipelines(uri, version)

@router.get(
    "/{pipeline_name}",
    response_model=Pipeline,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
    summary="Get information about one pipeline.",
)
async def get_pipeline(pipeline_name: str,
                       db_accessor=Depends(get_DbAccessor)):
    pipeline = None
    try:
        pipeline = await db_accessor.get_pipeline_by_name(name=pipeline_name)
    except NoResultFound:
        raise HTTPException(status_code=404,
                            detail=f"Pipeline '{pipeline_name}' not found")
    return pipeline

@router.post(
    "/",
    response_model=Pipeline,
    summary="Create one pipeline record.",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Pipeline was created"},
        status.HTTP_400_BAD_REQUEST: {"description": "Insufficient pipeline properties provided"},
        status.HTTP_409_CONFLICT: {"description": "Pipeline already exists"}
    }
)
async def create_pipeline(pipeline: Pipeline, db_accessor=Depends(get_DbAccessor)) -> Pipeline:
    new_pipeline = None
    try:
        new_pipeline = await db_accessor.create_pipeline(pipeline)
    except IntegrityError as e:
        logging.error(str(e))
        if (re.search('NOT NULL', str(e))):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Pipeline must specify a name and URI and version')
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Pipeline already exists')
    return new_pipeline
