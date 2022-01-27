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
    Column, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import relationship

from .base import Base

from npg.porch.models import Pipeline as ModeledPipeline

class Pipeline(Base):
    '''
    A black box of science
    '''
    __tablename__ = 'pipeline'
    pipeline_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    repository_uri = Column(String)
    version = Column(String)

    UniqueConstraint('repository_uri', 'version', name='unique_pipeline')

    tasks = relationship('Task', back_populates='pipeline')

    tokens = relationship('Token', back_populates='pipeline')

    def convert_to_model(self):
        'Convert sqlalchemy object to npg_porch format'
        return ModeledPipeline(
            name=self.name,
            version=self.version,
            uri=self.repository_uri
        )
