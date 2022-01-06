# Copyright (c) 2021, 2022 Genome Research Ltd.
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
    Column, Integer, String
)
from sqlalchemy.orm import relationship

from .base import Base

class Agent(Base):
    '''
    An autonomous client that can take work units
    '''
    __tablename__ = 'agent'
    agent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)

    claimed_tasks = relationship(
        'Task'
    )
    events = relationship(
        'Event', back_populates='agent'
    )
