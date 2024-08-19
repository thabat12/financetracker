from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header
import httpx
from enum import Enum

from batch.config import Session, settings, yield_db, logger
from batch.routes.auth import verify_token
from db.models import *

plaid_router = APIRouter()


async def plaid_exchange_public_token(user_id, public_token):
    logger.info('/plaid/plaid_exchange_public_token')
    access_token = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f'{settings.test_plaid_url}/item/public_token/exchange',
                headers={'Content-Type': 'application/json'},
                json={
                    'client_id': settings.test_plaid_client_id,
                    'secret': settings.plaid_secret,
                    'public_token': public_token
                }
            )

            logger.info('/plaid/plaid_exchange_public_token: plaid endpoint /item/public_token/exchange called')

            resp = resp.json()
            access_token = resp['access_token']
    except Exception as e:
        logger.error('/plaid/plaid_exchange_public_token: plaid endpoint failed!')
        raise HTTPException(status_code=500, detail='Plaid Endpoint Failed!') from e
    

    try:
        async for dbsess in yield_db():
            async with dbsess.begin():
                cur_user = await dbsess.get(User, user_id)
                if not cur_user:
                    raise HTTPException(status_code=500, detail='User does not exist!')
                cur_user.access_key = access_token
                await dbsess.commit()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Database Update Failed!') from e

class GetPublicTokenRequest(BaseModel):
    user_id: str

async def plaid_get_public_token(uuid: str):
    logger.info('/plaid/plaid_get_public_token: called')
    async for dbsess in yield_db():
        async with dbsess.begin():
            public_token = None
            try:
                async with httpx.AsyncClient() as client:
                    logger.info('/plaid/plaid_get_public_token: calling plaid endpoint /sandbox/public_token/create')
                    resp = await client.post(f'{settings.test_plaid_url}/sandbox/public_token/create',
                                            headers={'Content-Type': 'application/json'},
                                            json={
                                                'client_id': settings.test_plaid_client_id,
                                                'secret': settings.plaid_secret,
                                                'institution_id': 'ins_20',
                                                'initial_products': ['transactions'],
                                                'options': {
                                                    'webhook': 'https://www.plaid.com/webhook'
                                                }
                                            })
                    resp = resp.json()
                    public_token = resp['public_token']
                    logger.info('/plaid/plaid_get_pubic_token: public token created')
            except Exception as e:
                logger.error('/plaid/plaid_get_public_token: plaid endpoint request failed')
                raise HTTPException(status_code=500, detail='Plaid Endpoint Request Failed') from e
            
            return public_token
    return None

class LinkAccountResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'
    ALREADY_LINKED = 'already_linked'

class LinkAccountResponse(BaseModel):
    message: LinkAccountResponseEnum

@plaid_router.post('/link_account')
async def link_account(authorization: str = Header(...)):
    logger.info('/plaid/link_account: called')
    token = authorization.strip().split(' ')[-1].strip()

    # for every plaid endpoint, must verify the authentication token from now on
    (res, cur_user_id) = await verify_token(token)

    if not res:
        logger.info(f'/plaid/link_account: {cur_user_id} auth_session is invalid')
        return LinkAccountResponse(message=LinkAccountResponseEnum.INVALID_AUTH)

    # first make sure that the user is not already linked
    async with Session() as session:
        async with session.begin():
            cur_user: User = await session.get(User, cur_user_id)
            if cur_user.access_key is not None:
                logger.error(f'/plaid/link_account: {cur_user_id} the account is already linked!')
                return LinkAccountResponse(message=LinkAccountResponseEnum.ALREADY_LINKED)

    logger.info(f'/plaid/link_account: {cur_user_id} token is being generated')
    public_token = await plaid_get_public_token(cur_user_id)
    await plaid_exchange_public_token(cur_user_id, public_token)
        
    return LinkAccountResponse(message=LinkAccountResponseEnum.SUCCESS)