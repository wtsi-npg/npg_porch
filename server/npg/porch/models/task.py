from pydantic import BaseModel
from typing import Optional, List

from ...porch.models.pipeline import Pipeline
from ...porch.models.analysis import Analysis

class Task(BaseModel):
    pipeline: Pipeline
    analysis: Analysis
    analysis_id: Optional[str]
    task_input_id: str
    task_input: Optional[List[str]]
    status: str
