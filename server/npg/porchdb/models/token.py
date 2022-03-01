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
import uuid

from .base import Base

class Token(Base):
    '''
    A string token ussued to client applications for the purpose of
    authorizing them to perform certain actions.
    '''

    def random_token():
        '''
        Returns a 32 characters long random string. The chance of a
        collision is small.
        '''
        return str(uuid.uuid4()).replace("-", "")

    __tablename__ = 'token'
    token_id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(length=32), unique=True, default=random_token)
    description = Column(String, nullable=False)
    pipeline_id = Column(Integer, ForeignKey('pipeline.pipeline_id'),
                         nullable=False)
    date_issued = Column(DateTime, default=sqlalchemy.sql.functions.now())
    date_revoked = Column(DateTime, nullable=True)

    pipeline = relationship(
        'Pipeline', back_populates='tokens'
    )
    events = relationship(
        'Event', back_populates='token'
    )

    def __repr__(self):
        return "<Token(token_id='%i', description='%s', pipeline='%s')>" % (
               self.token_id, self.description, self.pipeline.name)
