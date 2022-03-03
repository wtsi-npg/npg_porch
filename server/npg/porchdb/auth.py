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

import logging
import re
from sqlalchemy import select
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from fastapi import HTTPException

from npg.porchdb.models import Token
from npg.porch.models.permission import Permission, RolesEnum

AUTH_TOKEN_LENGTH = 32

class Validator:
    '''
    A validator for credentials presented by the requestor.

    Instantiate with a sqlalchemy AsyncSession
    '''

    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(__name__)

    async def token2permission(self, token: str):

        message = None

        if len(token) != AUTH_TOKEN_LENGTH:
            message = f"The auth token should be {AUTH_TOKEN_LENGTH} chars long"
        else:
            prog = re.compile(r'\w{32}', flags=re.ASCII)
            if prog.match(token) is None:
                message = 'Token failed character validation'

        valid_token_row = None
        if message is None:
            try:
                result = await self.session.execute(
                    select(Token)
                    .filter_by(token=token)
                    .join(Token.pipeline)
                    .options(contains_eager(Token.pipeline))
                )
                valid_token_row = result.scalar_one()
            except NoResultFound:
                message = 'An unknown token is used'

        if (valid_token_row is not None) and (valid_token_row.date_revoked is not None):
            message = 'A revoked token is used'

        if message:
            self.logger.warning(message)
            raise HTTPException(status_code=403, detail="Invalid token")

        permission = None
        pipeline = valid_token_row.pipeline
        token_id = valid_token_row.token_id
        if pipeline is None:
            permission = Permission(
                role = RolesEnum.POWER_USER,
                requestor_id = token_id
            )
        else:
            permission = Permission(
                role = RolesEnum.REGULAR_USER,
                requestor_id = token_id,
                pipeline = pipeline.convert_to_model()
            )

        return permission
