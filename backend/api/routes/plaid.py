from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
import httpx
from enum import Enum
from sqlalchemy import select, update

from api.config import Session, settings, yield_db, logger
from api.routes.auth import verify_token
from db.models import *
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data

plaid_router = APIRouter()


async def plaid_exchange_public_token(user_id: str, public_token: str, institution_id: str):
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
                cur_user: User
                cur_user = await dbsess.get(User, user_id)
                if not cur_user:
                    raise HTTPException(status_code=500, detail='Error linking!')
                
                logger.info(f'/plaid/plaid_exchange_public_token: {user_id} adding the new access key under AccessKey table')
                # figure out if this user:institution exists in the table already
                access_key_id = f'{cur_user.user_id}:/:/:{institution_id}'
                cur_access_key = await dbsess.get(AccessKey, access_key_id)
                user_key = decrypt_data(cur_user.user_key, db_key_bytes)

                if not cur_access_key:
                    logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} creating new entry for current access key')
                    a = AccessKey(
                        access_key_id=access_key_id, 
                        access_key=encrypt_data(bytes(access_token, encoding='utf-8'), user_key),
                        user_id=cur_user.user_id               
                    )
                    dbsess.add(a)
                    logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} finished adding new access key entry to user')
                else:
                    logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} updating the access key')
                    await dbsess.execute(
                        update(AccessKey).values(
                            access_key=encrypt_data(bytes(access_token, encoding='utf-8'), user_key)
                        ).where(AccessKey.access_key_id == access_key_id)
                    )
                    logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} updated entry for access key to user')

                await dbsess.commit()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Database Update Failed!') from e

class GetPublicTokenRequest(BaseModel):
    user_id: str

async def plaid_get_public_token(uuid: str, institution_id: str):
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
                                                'institution_id': institution_id,
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

async def db_update_institution_details(institution_id: str):
    logger.info('/plaid/db_update_institution_details')
    async with Session() as session:
        async with session.begin():
            logger.info(f'/plaid/db_update_institution_details: checking to see if {institution_id} already exists in db or not')
            # ensure that the institution_id doesn't already exist in the database
            cur_institution = await session.get(Institution, institution_id)

            if cur_institution is not None:
                logger.info(f'/plaid/db_update_institution_details: {institution_id} already exists inthe db! no need for update!')
                # !!! EARLY RETURN (bad practice but yeah)
                return
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f'https://sandbox.plaid.com/institutions/get_by_id',
                    headers={
                        'Content-Type': 'application/json'
                    },
                    json={
                        'institution_id': institution_id,
                        'client_id': settings.test_plaid_client_id,
                        'secret': settings.plaid_secret,
                        'country_codes': ['US'],
                        'options': {
                            'include_optional_metadata': True
                        }
                    }
                )

                resp = resp.json()

            if 'error_code' in resp:
                logger.error(f'/plaid/db_update_institution_details: {institution_id} does not exist on Plaid!')
                raise HTTPException(detail='Institution ID does not exist on Plaid\'s records!', status_code=500)
            
            logger.info(f'/plaid/db_update_institution_details: {institution_id} the plaid endpoint is called and data retrieved')
            
            supported_products = set(resp['institution']['products'])
            institution_name = resp['institution']['name']
            institution_logo = resp['institution']['logo']
            institution_url = resp['institution']['url']

            new_ins = Institution(
                institution_id=institution_id,
                name=institution_name,
                supports_transactions='transactions' in supported_products,
                supports_auth='auth' in supported_products,
                supports_investments='investments' in supported_products,
                logo=institution_logo,
                url=institution_url
            )

            session.add(new_ins)
            await session.commit()
    logger.info(f'/plaid/db_update_institution_details: {institution_id} added to the database, and we are done!')

class LinkAccountResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'
    ALREADY_LINKED = 'already_linked'

class LinkAccountResponse(BaseModel):
    message: LinkAccountResponseEnum

class LinkAccountRequest(BaseModel):
    institution_id: str

@plaid_router.post('/link_account')
async def link_account(request: LinkAccountRequest, background_tasks: BackgroundTasks, authorization: str = Header(...)) -> LinkAccountResponse:
    logger.info('/plaid/link_account: called')
    token = authorization.strip().split(' ')[-1].strip()

    # for every plaid endpoint, must verify the authentication token from now on
    (res, cur_user_id) = await verify_token(token)

    if not res:
        logger.info(f'/plaid/link_account: {cur_user_id} auth_session is invalid')
        return LinkAccountResponse(message=LinkAccountResponseEnum.INVALID_AUTH)

    institution_id = request.institution_id

    logger.info(f'/plaid/link_account: registering background task to update institution id data for {institution_id}')
    background_tasks.add_task(db_update_institution_details, institution_id)

    logger.info(f'/plaid/link_account: {cur_user_id} public token is being generated')
    public_token = await plaid_get_public_token(cur_user_id, institution_id)
    await plaid_exchange_public_token(cur_user_id, public_token, institution_id)
        
    return LinkAccountResponse(message=LinkAccountResponseEnum.SUCCESS)