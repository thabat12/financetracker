from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from db.models import *
from api.config import yield_db, logger
from api.api_utils.auth_util import verify_token, decrypt_user_key
from api.api_utils.data_util import db_get_accounts, db_get_transactions
from api.api_utils.data_util import GetAccountsResponse, GetTransactionsResponse


data_router = APIRouter()

'''
    base dependencies for every api task in data.py:
        - verify_token_dependency: validate the API access key
        - decrypt_user_key_dependency: reading/ writing data requires a user key to
            properly handle encryption of any sensitive data
'''
async def session_dependency(session=Depends(yield_db)) -> AsyncSession:
    logger.info("SESSION DEPENDENCY CREATED NEW SESSION")
    return session

async def verify_token_dependency(
        cur_user: tuple[bool, str] = Depends(verify_token)) -> str:
    return cur_user[1]

async def decrypt_user_key_dependency(
        cur_user: str = Depends(verify_token_dependency),
        session: AsyncSession = Depends(session_dependency)) -> bytes:
    return decrypt_user_key(cur_user=cur_user, session=session)

'''
    route: '/data/get_accounts'
        read-only on the database, fast and reliable
'''
async def db_get_accounts_dependency(
        cur_user: str = Depends(verify_token_dependency),
        user_key: bytes = Depends(decrypt_user_key_dependency),
        session: AsyncSession = Depends(session_dependency)) -> GetAccountsResponse:
    
    all_accounts: GetAccountsResponse = db_get_accounts(cur_user=cur_user, user_key=user_key, \
                                                        session=session)

    return all_accounts

@data_router.post('/get_accounts')
async def get_accounts(all_accounts: GetAccountsResponse = Depends(db_get_accounts_dependency)):
    return all_accounts


'''
    route: '/data/get_transactions'
        read-only on the database, fast and reliable
'''
async def db_get_transactions_dependency(
        cur_user: str = Depends(verify_token_dependency),
        user_key: bytes = Depends(decrypt_user_key_dependency),
        session: AsyncSession = Depends(session_dependency)) -> GetTransactionsResponse:

    all_transactions: GetTransactionsResponse = await db_get_transactions(cur_user=cur_user, \
                                                        user_key=user_key, session=session)
    return all_transactions

@data_router.post('/get_transactions')
async def get_transactions(all_transactions: GetTransactionsResponse = Depends(db_get_transactions_dependency)):
    return all_transactions