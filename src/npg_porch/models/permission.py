# Copyright (C) 2022. 2023 Genome Research Ltd.
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

from enum import Enum
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional

from npg_porch.models.pipeline import Pipeline


class PermissionValidationException(Exception):
    pass


class RolesEnum(str, Enum):
    def __str__(self):
        return self.value

    POWER_USER = "power_user"
    REGULAR_USER = "regular_user"


class Permission(BaseModel):
    pipeline: Optional[Pipeline] = Field(
        None,
        title="An optional pipeline object",
        description="The scope is limited to this pipeline if undefined",
    )
    requestor_id: int = Field(
        title="ID that corresponds to the presented credentials",
        description="A validated internal ID that corresponds to the presented credentials",
    )
    role: RolesEnum = Field(
        title="A role associated with the presented credentials",
    )

    @field_validator("role")
    @classmethod
    def no_pipeline4special_users(cls, v: str, info: ValidationInfo):
        if v == RolesEnum.POWER_USER and (
            "pipeline" in info.data and info.data["pipeline"] is not None
        ):
            raise ValueError("Power user cannot be associated with a pipeline")

        return v

    def validate_pipeline(self, pipeline: Pipeline):
        if self.role != RolesEnum.REGULAR_USER:
            raise PermissionValidationException(
                f"Operation is not valid for role {self.role}"
            )
        if not self.pipeline:
            raise PermissionValidationException("No associated pipeline object")

        if pipeline.name != self.pipeline.name:
            raise PermissionValidationException(
                "Token-request pipeline mismatch: "
                + f"'{self.pipeline.name}' and '{pipeline.name}'"
            )

        pass
