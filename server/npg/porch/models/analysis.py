from pydantic import BaseModel
from typing import Dict

class Analysis(BaseModel):
    args: Dict
