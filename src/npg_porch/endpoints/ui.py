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

from fastapi import APIRouter, Depends, Request
from starlette import status

from npg_porch.db.connection import get_DbAccessor

router = APIRouter(
    prefix="/ui",
    tags=["ui"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected error"},
    },
)


@router.get(
    "/tasks",
    response_model=dict,
    summary="Returns all expanded tasks in a displayable format for the ui",
)
async def get_ui_tasks(request: Request, db_accessor=Depends(get_DbAccessor)) -> dict:
    params = request.query_params.get
    task_list = await db_accessor.get_expanded_tasks()
    return {"draw": params("draw"), "recordsTotal": len(task_list), "data": task_list}


@router.get(
    "/tasks/{pipeline_name}",
    response_model=dict,
    summary="Returns all expanded tasks for the specified pipeline in a "
    "displayable format for the ui",
)
async def get_ui_pipeline_tasks(
    request: Request, pipeline_name: str, db_accessor=Depends(get_DbAccessor)
) -> dict:
    params = request.query_params.get
    task_list = await db_accessor.get_expanded_tasks(pipeline_name)
    return {"draw": params("draw"), "recordsTotal": len(task_list), "data": task_list}
