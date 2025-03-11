# Copyright (C) 2021, 2022, 2023 Genome Research Ltd.
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
from datetime import datetime
from enum import Enum
import hashlib
import ujson
from pydantic import BaseModel, Field, ValidationError

from npg_porch.models.pipeline import Pipeline


class TaskStateEnum(str, Enum):
    def __str__(self):
        return self.value

    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    pipeline: Pipeline
    task_input_id: str | None = Field(
        None,
        title="Task Input ID",
        description="A stringified unique identifier for a piece of work. Set by the npg_porch server, not the client",  # noqa: E501
    )
    task_input: dict = Field(
        None,
        title="Task Input",
        description="A structured parameter set that uniquely identifies a piece of work, and enables an iteration of a pipeline",  # noqa: E501
    )
    status: TaskStateEnum

    def generate_task_id(self):
        return hashlib.sha256(
            ujson.dumps(self.task_input, sort_keys=True).encode()
        ).hexdigest()

    def __eq__(self, other):
        """
        Allow instances of Task to be compared with ==

        The pipeline and task_input_ids can partially differ and it still be a
        valid comparison. Clients do not get to create task_input_ids and may
        not fully specify a pipeline.

        Automatically attempts to cast a dict into a Task, and therefore
        ignores any properties not valid for a Task

        """
        if isinstance(other, dict):
            try:
                other = Task.model_validate(other)
            except ValidationError:
                return False

        if not isinstance(other, Task):
            return False

        truths = []
        for k, v in self.model_dump().items():
            other_d = other.model_dump()
            if k == "pipeline":
                truths.append(v["name"] == other_d[k]["name"])
            elif k == "task_input_id":
                break
            elif k == "status":
                break  # or maybe compare?
            else:
                truths.append(v == other_d[k])
        if all(truths):
            return True

        return False


class TaskExpanded(Task):
    """
    An expanded task model for serving a web page.

    Dates are formatted to improve human readability.
    """

    created: datetime = Field(
        default=None,
        title="Task Created",
        description="The timestamp of task creation",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.strftime("%Y-%m-%d\u00A0%H:%M:%S")}
