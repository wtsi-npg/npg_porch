from pydantic import BaseModel

class Pipeline(BaseModel):
    name: str
    version: str
