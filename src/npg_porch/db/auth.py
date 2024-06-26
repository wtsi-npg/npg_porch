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

import re
from sqlalchemy import select
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound

from npg_porch.db.models import Token
from npg_porch.models.permission import Permission, RolesEnum

__AUTH_TOKEN_LENGTH__ = 32
__AUTH_TOKEN_REGEXP__ = re.compile(
    r'\A[0-9A-F]+\Z', flags = re.ASCII | re.IGNORECASE)

class CredentialsValidationException(Exception):
    pass


class Validator:
    '''
    A validator for credentials presented by the requestor.

    Instantiate with a sqlalchemy AsyncSession
    '''

    def __init__(self, session):
        self.session = session

    async def token2permission(self, token: str):

        if len(token) != __AUTH_TOKEN_LENGTH__:
            raise CredentialsValidationException(
                f"The token should be {__AUTH_TOKEN_LENGTH__} chars long"
            )
        elif __AUTH_TOKEN_REGEXP__.match(token) is None:
            raise CredentialsValidationException(
                'Token failed character validation'
            )

        try:
            # Using 'outerjoin' to get the left join for token, pipeline.
            # We need to retrieve all token rows, regardless of whether
            # they are linked the pipeline table or not (we are using a
            # nullable foreign key to allow for no link).
            result = await self.session.execute(
                select(Token)
                .filter_by(token=token)
                .outerjoin(Token.pipeline)
                .options(contains_eager(Token.pipeline))
            )
            valid_token_row = result.scalar_one()
        except NoResultFound:
            raise CredentialsValidationException('An unknown token is used')

        if (valid_token_row is not None) and (valid_token_row.date_revoked is not None):
            raise CredentialsValidationException('A revoked token is used')

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
