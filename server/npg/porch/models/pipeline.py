from pydantic import BaseModel, Field
from typing import Optional

class Pipeline(BaseModel):
    name: str = Field(
        None,
        title='Pipeline Name',
        description='A user-controlled name for the pipeline'
    )
    version: Optional[str] = 'latest'
    uri: Optional[str] = Field(
        None,
        title='URI',
        description='URI to bootstrap the pipeline code'
    )
