import hashlib
import ujson
from pydantic import BaseModel, Field
from typing import Optional, Dict

from npg.porch.models.pipeline import Pipeline

class Task(BaseModel):
    pipeline: Pipeline
    task_input_id: Optional[str] = Field(
        None,
        title='Task Input ID',
        description='A stringified unique identifier for a piece of work. Set by the npg_porch server, not the client'
    )
    task_input: Dict = Field(
        None,
        title='Task Input',
        description='A structured parameter set that uniquely identifies a piece of work, and enables an iteration of a pipeline'
    )
    status: Optional[str]

    def generate_analysis_id(self):
        return hashlib.sha256(ujson.dumps(self.analysis, sort_keys=True).encode()).hexdigest()
