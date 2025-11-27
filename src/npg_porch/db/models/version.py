# Copyright (C) 2025 Genome Research Ltd.
#
# Author: Michael Kubiak mk35@sanger.ac.uk
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

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base

from npg_porch.models import Pipeline as ModeledPipeline


class Version(Base):
    """
    A pipeline version
    """

    __tablename__ = "version"
    version_id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, nullable=False)
    pipeline_id = Column(Integer, ForeignKey("pipeline.pipeline_id"), nullable=False)
    unique_version = UniqueConstraint(version, pipeline_id, name="unique_version")

    pipeline = relationship("Pipeline", back_populates="versions")
    tasks = relationship("Task", back_populates="version")

    def convert_to_api_pipeline(self):
        """
        Convert sqlalchemy object to npg_porch format.
        """
        return ModeledPipeline(
            version=self.version,
            name=self.pipeline.name,
            uri=self.pipeline.repository_uri,
        )
