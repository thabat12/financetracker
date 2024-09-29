from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from db.models import *
from api.config import yield_db, yield_client
from api.api_utils.auth_util import verify_token, decrypt_user_key
from api.api_utils.data_util import db_get_accounts
from api.api_utils.data_util import GetAccountsResponse


data_router = APIRouter()

'''
'''
async def verify_token_dependency(
        cur_user: tuple[bool, str] = Depends(verify_token)) -> str:
    return cur_user[1]

async def decrypt_user_key_dependency(
        cur_user: str = Depends(verify_token_dependency),
        session: AsyncSession = Depends(yield_db)) -> bytes:
    return decrypt_user_key(cur_user=cur_user, session=session)

async def db_get_accounts_dependency(
        cur_user: str = Depends(verify_token_dependency),
        user_key: bytes = Depends(decrypt_user_key_dependency),
        session: AsyncSession = Depends(yield_db)) -> GetAccountsResponse:
    
    all_accounts: GetAccountsResponse = db_get_accounts(cur_user=cur_user, user_key=user_key, \
                                                        session=session)

@data_router.post('/get_accounts')
async def get_accounts(all_accounts: GetAccountsResponse = Depends(db_get_accounts_dependency)):
    return all_accounts