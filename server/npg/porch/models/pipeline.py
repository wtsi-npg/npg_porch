from pydantic import BaseModel
from typing import Optional

class Pipeline(BaseModel):
    name: str
    version: Optional[str] = 'latest'
    uri: Optional[str]
