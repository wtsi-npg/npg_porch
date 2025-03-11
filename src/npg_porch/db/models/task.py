# Copyright (C) 2021, 2022 Genome Research Ltd.
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

from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    UniqueConstraint,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import now
from sqlalchemy.sql.sqltypes import DateTime

from .base import Base
from npg_porch.models import Task as ModelledTask, TaskExpanded as ModelledTaskExpanded


class Task(Base):
    """
    A unique combination of inputs for an Pipeline
    """

    __tablename__ = "task"
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("pipeline.pipeline_id"))
    job_descriptor = Column(String)
    # This is the serialisation of Dict representing the JSON
    # provided by the workflow - we don't want to get into serialising
    # and deserialising from job_descriptor above, so we keep the original
    definition = Column(JSON)
    # WARNING: JSON type requires sqlite 3.9+ installed on the host system
    # and the JSON1 plugin enabled.
    state = Column(String)
    # prefix is a special property for uniquifying folder names
    # or LSF job names and so on.
    prefix = Column(String)
    created = Column(DateTime, default=now())

    # Set unique this way so that SQLite creates the constraint
    __table_args__ = (
        UniqueConstraint("pipeline_id", "job_descriptor", name="unique_tasks"),
    )

    # Index('idx_unique_tasks', pipeline_id, job_descriptor, unique=True)
    Index("idx_ordered_tasks", pipeline_id, created)

    pipeline = relationship("Pipeline", back_populates="tasks")
    events = relationship("Event", back_populates="task")

    def convert_to_model(
        self, task_class: type[ModelledTask | ModelledTaskExpanded] = ModelledTask
    ) -> ModelledTask | ModelledTaskExpanded:
        init_args = {
            "pipeline": self.pipeline.convert_to_model(),
            "task_input_id": self.job_descriptor,
            "task_input": self.definition,
            "status": self.state,
        }
        if task_class == ModelledTaskExpanded:
            init_args["created"] = self.created
        return task_class(**init_args)
