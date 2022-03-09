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
        logger.warning(e)
        raise HTTPException(status_code=403, detail="Invalid token")

    return p
