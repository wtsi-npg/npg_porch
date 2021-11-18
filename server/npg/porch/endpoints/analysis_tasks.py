from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from ..endpoints.pipelines import Pipeline

class Task(BaseModel):
    name: str

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
    return [Task(name="mine"), Task(name="yours")]

@router.get(
    "/{task_name}",
    response_model=Task,
    summary="Get one analysis task.",
    description="Get one analysis task using its unique name."
)
def get_analysis_task(task_name: str):
    return Task(name=task_name)

@router.post(
    "/",
    response_model=Task,
    summary="Create one analysis task."
)
def create_analysis_task(task_name: str):
    return Task(name=task_name)

@router.put(
    "/",
    response_model=Task,
    summary="Update one analysis task."
)
def update_analysis_task(task: Task):
    return task;

@router.post(
    "/claim",
    response_model=Task,
    summary="Claim one analysis task.",
    description="Claim one analysis task for a particular pipeline."
)
def claim_analysis_task(pipeline: Pipeline):
    return Task(name="daa")


