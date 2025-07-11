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
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Depends, Request
from starlette import status

from npg_porch.db.connection import get_DbAccessor
from npg_porch.models import TaskStateEnum

DAY_ONE = datetime(1, 1, 1)


class UiStateEnum(str, Enum):
    def __str__(self):
        return self.value

    ALL = "All"
    NOT_DONE = "NOT DONE"


router = APIRouter(
    prefix="/ui",
    tags=["ui"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected error"},
    },
)


@router.get(
    "/tasks/{pipeline_name}/{state}/{since}",
    response_model=dict,
    summary="Returns all expanded tasks for the specified pipeline and status "
    "in a displayable format for the ui",
)
async def get_ui_tasks(
    request: Request,
    pipeline_name: str,
    state: TaskStateEnum | UiStateEnum,
    since: datetime = DAY_ONE,
    db_accessor=Depends(get_DbAccessor),
) -> dict:
    pipeline_name = None if pipeline_name == "All" else pipeline_name
    params = request.query_params.get
    since = None if since == DAY_ONE else since
    state = (
        [
            taskstate
            for taskstate in TaskStateEnum
            if taskstate not in [TaskStateEnum.DONE, TaskStateEnum.CANCELLED]
        ]
        if state == UiStateEnum.NOT_DONE
        else None
        if state == UiStateEnum.ALL
        else [state]
    )
    task_list = await db_accessor.get_expanded_tasks(pipeline_name, state, since)
    return {"draw": params("draw"), "recordsTotal": len(task_list), "data": task_list}


@router.get(
    "/long_running",
    response_model=dict,
    summary="Returns all long running tasks in a displayable format for the ui",
)
async def get_long_running_ui_tasks(
    request: Request, db_accessor=Depends(get_DbAccessor)
) -> dict:
    params = request.query_params.get
    task_list = await db_accessor.get_long_running_tasks()
    return {"draw": params("draw"), "recordsTotal": len(task_list), "data": task_list}
