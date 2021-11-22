from fastapi import APIRouter, HTTPException
from typing import List

from ..models.pipeline import Pipeline

router = APIRouter(
    prefix="/pipelines",
    tags=["pipelines"]
)

@router.get(
    "/",
    response_model=List[Pipeline],
    summary="Get information about all pipelines.",
    description="Get all pipelines. A filter will be applied if used in the query."
)
def get_pipelines():
    return [Pipeline(name="longranger", version="3.0")]

@router.get(
    "/{pipeline_id}",
    response_model=Pipeline,
    responses={404: {"description": "Not found"}},
    summary="Get information about one pipeline.",
)
def get_pipeline(pipeline_name: str):
    if pipeline_name != "longranger":
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return Pipeline(name="longranger", version="3.0")

@router.post(
    "/",
    response_model=Pipeline,
    summary="Create one pipeline record.",
)
def create_pipeline(pipeline: Pipeline):
    return pipeline

