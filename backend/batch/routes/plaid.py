from pydantic import BaseModel
from pydantic_settings import BaseSettings
from fastapi import APIRouter, HTTPException, Header
import httpx

from batch.config import Session, async_database_engine, settings, yield_db
from batch.routes.auth import verify_token
from db.models import *

plaid_router = APIRouter()


async def plaid_exchange_public_token(user_id, public_token):
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

            resp = resp.json()
            access_token = resp['access_token']
    except Exception as e:
        print(e)
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
    async for dbsess in yield_db():
        async with dbsess.begin():
            public_token = None
            try:
                async with httpx.AsyncClient() as client:
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
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail='Plaid Endpoint Request Failed') from e
            
            return public_token
    return None

@plaid_router.post('/link_account')
async def link_account(authorization: str = Header(...)):
    print(f'the authorization header value is: {authorization}')

    token = authorization.strip().split(' ')[-1].strip()

    print(f'parsed out token is {token}')

    # for every plaid endpoint, must verify the authentication token from now on
    (res, cur_user) = await verify_token(token)

    if res:
        print('token is valid!')

        print('getting public token')
        public_token = await plaid_get_public_token(cur_user)
        print('the public token is this:', public_token)
        await plaid_exchange_public_token(cur_user, public_token)
        print('and the public token is exchanged for access token, and user is set up!')
    else:
        print('token is invalid for some reason')

    return {
        'message': 'hi'
    }

class ExchangePublicTokenRequest(BaseModel):
    user_id: str
    public_token: str


@plaid_router.post('/exchange_public_token')
async def exchange_public_token(request: ExchangePublicTokenRequest):
    await plaid_exchange_public_token(request.user_id, request.public_token)
    return {'message': 'success'}

class GetTransactionsRequest(BaseModel):
    user_id: str