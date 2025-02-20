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

import sqlalchemy
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from .base import Base
from npg_porch.models import Event as ModelledEvent
from .task import Task

class Event(Base):
    '''
    A sequence of time-stamped state changes for each Task for
    reporting and metrics purposes.
    '''
    __tablename__ = 'event'
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey(Task.task_id))
    time = Column(DateTime, default=sqlalchemy.sql.functions.now())
    change = Column(String)
    token_id = Column(Integer, ForeignKey('token.token_id'), nullable=False)

    task = relationship(
        'Task'
    )

    # Consider adding 'order_by=Token.token_id'
    token = relationship(
        'Token', back_populates='events'
    )

    def convert_to_model(self):
        return ModelledEvent(
            time=self.time,
            change=self.change
        )
