from fastapi import Depends
from fastapi.security import HTTPBearer

from npg.porchdb.connection import get_CredentialsValidator

auth_scheme = HTTPBearer()

async def validate(
    creds = Depends(auth_scheme),
    validator = Depends(get_CredentialsValidator)
):
    token = creds.credentials
    p = await validator.token2permission(token)

    return p
