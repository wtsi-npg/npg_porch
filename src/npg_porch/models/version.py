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

from pydantic import BaseModel, ConfigDict, Field
from npg_porch.models import Pipeline


class Version(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: Pipeline
    version: str = Field(
        default=None,
        title="Version",
        description="The version string",
    )
