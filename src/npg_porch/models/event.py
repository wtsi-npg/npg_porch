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

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(extra='ignore')

    time: datetime = Field(
        default=None,
        title="Event Time",
        description="Timestamp of the event"
    )
    change: str | None = Field(
        default=None,
        title="Event Change",
        description="The change that occurred during the event"
    )

    def __lt__(self, other):
        return self.date < other.date

    def __gt__(self, other):
        return self.date > other.date

    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        # doesn't care about task, probably not a problem right now
        return self.date == other.date and self.change == other.change
