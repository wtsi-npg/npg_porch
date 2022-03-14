# Copyright (C) 2022 Genome Research Ltd.
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

import logging
from fastapi import Depends
from fastapi.security import HTTPBearer
from fastapi import HTTPException

from npg.porchdb.connection import get_CredentialsValidator
from npg.porchdb.auth import CredentialsValidationException

auth_scheme = HTTPBearer()

async def validate(
    creds = Depends(auth_scheme),
    validator = Depends(get_CredentialsValidator)
):

    token = creds.credentials
    p = None
    try:
        p = await validator.token2permission(token)
    except CredentialsValidationException as e:
        logger = logging.getLogger(__name__)
        logger.warning(str(e))
        raise HTTPException(status_code=403, detail="Invalid token")

    return p
