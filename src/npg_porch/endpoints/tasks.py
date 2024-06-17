# Copyright (C) 2021, 2022, 2023 Genome Research Ltd.
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

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from npg_porch.auth.token import validate
from npg_porch.models.permission import PermissionValidationException
from npg_porch.models.pipeline import Pipeline
from npg_porch.models.task import Task, TaskStateEnum
from npg_porch.db.connection import get_DbAccessor
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from starlette import status


def _validate_request(permission, pipeline):

    try:
        permission.validate_pipeline(pipeline)
    except PermissionValidationException as e:
        logger = logging.getLogger(__name__)
        logger.warning(str(e))
        raise HTTPException(
            status_code=403,
            detail=("Given credentials cannot be used for"
                    f" pipeline '{pipeline.name}'")
        )

        pass


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not authorised"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected error"}
    }
)


@router.get(
    "/",
    response_model=list[Task],
    summary="Returns all tasks, and can be filtered to task status or pipeline name",
    description='''
    Return all tasks. The list of tasks can be filtered by supplying a pipeline
    name and/or task status'''
)
async def get_tasks(
    pipeline_name: str | None = None,
    status: TaskStateEnum | None = None,
    db_accessor=Depends(get_DbAccessor),
    permission=Depends(validate)
) -> list[Task]:
    print(pipeline_name, status)
    return await db_accessor.get_tasks(pipeline_name=pipeline_name, task_status=status)


@router.post(
    "/",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Task creation was successful"},
        status.HTTP_409_CONFLICT: {"description": "A task with the same signature already exists"}
    },
    summary="Creates one task record.",
    description='''
    Given a Task object, creates a database record for it and returns
    the same object, the response HTTP status is 201 'Created'. The
    new task is assigned pending status, ie becomes available for claiming.

    The pipeline specified by the `pipeline` attribute of the Task object
    should exist. If it does not exist, return status 404 'Not found'.'''
)
async def create_task(
    task: Task,
    db_accessor=Depends(get_DbAccessor),
    permission=Depends(validate)
) -> Task:

    _validate_request(permission, task.pipeline)

    try:
        created_task = await db_accessor.create_task(
            token_id=permission.requestor_id,
            task=task
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail='Unable to create task, as another like it already exists'
        )
    except NoResultFound:
        raise HTTPException(status_code=404, detail='Failed to find pipeline for this task')

    return created_task


@router.put(
    "/",
    response_model=Task,
    responses={
        status.HTTP_200_OK: {"description": "Task was modified"},
    },
    summary="Update one task.",
    description='''
    Given a Task object, updates the status of the task in the database
    to the value of the status in this Task object.

    If the task does not exist, status 404 'Not found' is returned.'''
)
async def update_task(
    task: Task,
    db_accessor=Depends(get_DbAccessor),
    permission=Depends(validate)
) -> Task:

    _validate_request(permission, task.pipeline)

    try:
        changed_task = await db_accessor.update_task(
            token_id=permission.requestor_id,
            task=task
        )
    except NoResultFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return changed_task


@router.post(
    "/claim",
    response_model=list[Task],
    responses={
        status.HTTP_200_OK: {"description": "Receive a list of tasks that have been claimed"}
    },
    summary="Claim tasks for a particular pipeline.",
    description='''
    Arguments - the Pipeline object and the maximum number of tasks
    to retrieve and claim, the latter defaults to 1 if not given.

    If no tasks that satisfy the given criteria and are unclaimed
    are found, returns status 200 and an empty array.

    If any tasks are claimed, return an array of these Task objects
    and status 200.

    The pipeline object returned within each of the tasks is consistent
    with the pipeline object in the payload, but has all possible
    attributes defined (uri, version).'''
)
async def claim_task(
    pipeline: Pipeline,
    num_tasks: Annotated[int | None, Query(gt=0)] = 1,
    db_accessor=Depends(get_DbAccessor),
    permission=Depends(validate)
) -> list[Task]:

    _validate_request(permission, pipeline)
    tasks = await db_accessor.claim_tasks(
        token_id=permission.requestor_id,
        pipeline=pipeline,
        claim_limit=num_tasks
    )

    return tasks
