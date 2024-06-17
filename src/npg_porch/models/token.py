# Copyright (C) 2024 Genome Research Ltd.
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


class Token(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(
        default=None,
        title='Pipeline Name',
        description='A user-controlled name of an existing pipeline'
    )
    description: str | None = Field(
        default=None,
        title='Description',
        description='A user-controlled description of the token'
    )
    token: str | None = Field(
        default=None,
        title='Token',
        description='An authorisation token'
    )
