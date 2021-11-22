from fastapi import APIRouter, HTTPException
from typing import List

from ..models.pipeline import Pipeline
from ..models.task import Task

router = APIRouter(
    prefix="/analysis_tasks",
    tags=["analysis_tasks"]
)

@router.get(
    "/",
    response_model=List[Task],
    summary="Returns all analysis tasks.",
    description="Return all tasks. A filter will be applied if used in the query."
)
def get_analysis_tasks():
    return [
        Task(
            pipeline = Pipeline(name="mine"),
            analysis = Analysis(arg1="one", arg2="two"),
            analysis_id = "xsdsdsd",
            task_input_id = "sssssfffffff",
            task_input = ["/seq/4345/4346_1.bam","/seq/4345/4346_2.bam"],
            status = "COMPLETED"
        ),
        Task(
            pipeline = Pipeline(name="yours"),
            analysis = Analysis(arg1="one", arg2="two"),
            analysis_id = "xsdsdsd",
            task_input_id = "fdgdfgfgdg",
            task_input = ["/seq/4345/4345_1.bam","/seq/4345/4345_2.bam"],
            status = "PENDING"
        )
    ]

#@router.get(
#    "/{task_name}",
#    response_model=Task,
#    summary="Get one analysis task.",
#    description="Get one analysis task using its unique name."
#)
#def get_analysis_task(task_name: str):
#    return Task(name=task_name)

@router.post(
    "/",
    response_model=Task,
    summary="Create one analysis task."
)
def create_analysis_task(task: Task):
    """
    Given a Task object, creats a database record for it and returns
    the same object with status 201 'Created'

    The pipeline specified by the `pipeline` attribute of the Task object
    should exist. If it does not exist, return status 404 'Not found' and
    an error.

    Errors if task status is not PENDING.
    """
    return task

@router.put(
    "/",
    response_model=Task,
    summary="Update one analysis task."
)
def update_analysis_task(task: Task):
    """
    Given a Task object, updates the status of the task in the database.
    
    The pipeline specified by the `pipeline` attribute of the Task object
    should exist. If it does not exist, return status 404 'Not found' and
    an error.
    
    The analysis specified by the `analysis` attribute of the Task object
    should exist. If it does not exist, return status 404 'Not found' and
    an error.

    If the `analysis_id` attribute of the Task object is defined it should
    correspond to the `analysis` attribute of the object. If not, return
    status 409 'Conflict'. (Do we check this here or in the db client?).
    """
    return task;

@router.post(
    "/claim",
    response_model=List[Task],
    summary="Claim analysis tasks.",
    description="Claim analysis tasks for a particular pipeline."
)
def claim_analysis_task(pipeline: Pipeline, num_tasks: int = 1) -> List[Task]:
    """
    Arguments - the Pipeline object and the maximum number of tasks
    to retrieve and claim, the latter defaults to 1 if not given.  
    
    Return an error and status 404 'Not Found' if the pipelime with the
    given name does not exist.
   
    Do not accept requests for non-current pipelines or their versions,
    check for the up-to-date db value. Return an error and status 406
    'Not acceptable' or 409 'Conflict'.
    
    If the version is specified as `latest`, retrieve tasks for
    the latest version, otherwise, retrieve tasks for the specified
    version.

    It is possible that no tasks that satisfy the given criteria and
    are unclaimed are found. Return status 200 and an empty array.

    If any tasks are claimed, return an array of these Task objects and
    status 200.
    """

    # The pipeline object returned within the Task should be consistent
    # with the pipeline object in the payload, but, typically, will have
    # more attributes defined (uri, teh specific version). 
    return [Task(
                pipeline = Pipeline(name="yours"),
                analysis = Analysis(arg1="one", arg2="two"),
                analysis_id = "xsdsdsd",
                task_input_id = "fdgdfgfgdg",
                task_input = ["/seq/4345/4345_1.bam","/seq/4345/4345_2.bam"],
                status = "PENDING"
            )]

