from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header, Depends
import httpx
from enum import Enum
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Session, settings, yield_client, yield_db, logger
from api.api_utils.auth_util import verify_token
from db.models import *
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data

TEST_PLAID_URL = settings.test_plaid_url

'''
    Models: 

'''
class BreakdownModel(BaseModel):
    success: float
    error_plaid: float
    error_institution: float
    refresh_interval: Optional[str] = None  # Only appears in some breakdowns

class StatusDetailModel(BaseModel):
    status: str
    last_status_change: datetime
    breakdown: BreakdownModel

class StatusModel(BaseModel):
    item_logins: StatusDetailModel
    transactions_updates: StatusDetailModel
    auth: StatusDetailModel
    identity: StatusDetailModel
    investments: Optional[StatusDetailModel] = None
    liabilities: Optional[StatusDetailModel] = None
    investments_updates: Optional[StatusDetailModel] = None
    liabilities_updates: Optional[StatusDetailModel] = None

class InstitutionModel(BaseModel):
    country_codes: List[str]
    institution_id: str
    name: str
    products: List[str]
    routing_numbers: Optional[List[str]] = None
    dtc_numbers: Optional[List[str]] = None
    oauth: bool
    status: StatusModel
    primary_color: Optional[str] = None
    url: str
    logo: Optional[str] = None

class InstitutionsGetByIdResponse(BaseModel):
    institution: InstitutionModel
    request_id: str

class GetPublicTokenRequest(BaseModel):
    user_id: str

class LinkAccountResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'
    ALREADY_LINKED = 'already_linked'

class LinkAccountResponse(BaseModel):
    message: LinkAccountResponseEnum

class LinkAccountRequest(BaseModel):
    institution_id: str

'''
    Util functions: 
'''
async def plaid_get_institution_by_id(institution_id: str) -> InstitutionsGetByIdResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{TEST_PLAID_URL}/institutions/get_by_id',
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
    
    return InstitutionsGetByIdResponse(**resp)


async def db_update_institution_details(request: LinkAccountRequest, session: AsyncSession):
    logger.info('/plaid/db_update_institution_details')

    institution_id = request.institution_id

    logger.info(f'/plaid/db_update_institution_details: checking to see if {institution_id} already exists in db or not')
    # ensure that the institution_id doesn't already exist in the database
    cur_institution = await session.get(Institution, institution_id)

    if cur_institution is not None:
        logger.info(f'/plaid/db_update_institution_details: {institution_id} already exists in the db! no need for update!')
        # !!! EARLY RETURN (bad practice but yeah)
        return await session.get(Institution, institution_id)
    
    institution_data = await plaid_get_institution_by_id(institution_id = institution_id)
    logger.info(f'/plaid/db_update_institution_details: {institution_id} the plaid endpoint is called and data retrieved')
    
    supported_products = set(institution_data.institution.products)
    institution_name = institution_data.institution.name
    institution_logo = institution_data.institution.logo
    institution_url = institution_data.institution.url

    new_ins = Institution(
        institution_id=institution_id,
        name=institution_name,
        supports_transactions='transactions' in supported_products,
        supports_investments='investments' in supported_products,
        logo=institution_logo,
        url=institution_url
    )

    session.add(new_ins)
    await session.commit()
    logger.info(f'/plaid/db_update_institution_details: {institution_id} added to the database, and we are done!')
    return new_ins

async def plaid_get_public_token(ins_details: Institution, client: AsyncSession = Depends(yield_client)) -> str:
    logger.info('/plaid/plaid_get_public_token: called')

    public_token = None
    transactions, investments = ins_details.supports_transactions, ins_details.supports_investments
    institution_id = ins_details.institution_id

    products = []
    if transactions:
        products.append('transactions')
    if investments:
        products.append('investments')

    logger.info(f'/plaid/plaid_get_public_token endpoint calling {institution_id} with products as: {products}')

    logger.info('/plaid/plaid_get_public_token: calling plaid endpoint /sandbox/public_token/create')

    try:
        resp = await client.post(f'{settings.test_plaid_url}/sandbox/public_token/create',
                        headers={'Content-Type': 'application/json'},
                        json={
                            'client_id': settings.test_plaid_client_id,
                            'secret': settings.plaid_secret,
                            'institution_id': institution_id,
                            'initial_products': products,
                            'options': {
                                'webhook': 'https://www.plaid.com/webhook'
                            }
                        })
        resp = resp.json()
        public_token = resp['public_token']
        logger.info('/plaid/plaid_get_pubic_token: public token created')
    except httpx.ReadTimeout as e:
        logger.error('there is a read timeout!')
        raise HTTPException(status_code=500, detail='Plaid Endpoint Read Timeout') from e
    except Exception as e:
        print(e)
        logger.error('/plaid/plaid_get_public_token: plaid endpoint request failed')
        
        raise HTTPException(status_code=500, detail='Plaid Endpoint Request Failed') from e
    
    return public_token

# returns the plaid access token
async def exchange_public_token(public_token: str, client: httpx.AsyncClient = Depends(yield_client)) -> str:
    logger.info('/plaid/plaid_exchange_public_token')
    access_token = None
    try:
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
    
    return access_token

async def update_user_access_key(access_key: str, cur_user: str, ins_details: Institution, session: AsyncSession = Depends(yield_db)):
    cur_user: User
    institution_id = ins_details.institution_id
    cur_user = await session.get(User, cur_user)
    if not cur_user:
        raise HTTPException(status_code=500, detail='Error linking!')
    
    logger.info(f'/plaid/plaid_exchange_public_token: {cur_user} adding the new access key under AccessKey table')
    # figure out if this user:institution exists in the table already
    access_key_id = f'{cur_user.user_id}:/:/:{institution_id}'
    cur_access_key = await session.get(AccessKey, access_key_id)
    user_key = decrypt_data(cur_user.user_key, db_key_bytes)

    if not cur_access_key:
        logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} creating new entry for current access key')
        a = AccessKey(
            access_key_id=access_key_id, 
            access_key=encrypt_data(bytes(access_key, encoding='utf-8'), user_key),
            user_id=cur_user.user_id               
        )
        session.add(a)
        logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} finished adding new access key entry to user')
    else:
        logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} updating the access key')
        await session.execute(
            update(AccessKey).values(
                access_key=encrypt_data(bytes(access_key, encoding='utf-8'), user_key)
            ).where(AccessKey.access_key_id == access_key_id)
        )
        logger.info(f'/plaid/plaid_exchange_public_token: {cur_user.user_id} updated entry for access key to user')

    await session.commit()

'''
    Database Modification Operations: 
'''