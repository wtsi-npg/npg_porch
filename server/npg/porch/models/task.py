# Copyright (c) 2021 Genome Research Ltd.
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

    @staticmethod
    def generate_analysis_id(self):
        return hashlib.sha256(ujson.dumps(self.task_input, sort_keys=True).encode()).hexdigest()
