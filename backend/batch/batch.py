import httpx
import signal
import asyncio
import secrets
import string
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from batch.config import Config
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

from db.models import *

Session: AsyncSession | None = None
class Settings(BaseSettings):
        async_sqlalchemy_database_uri: str
        sqlalchemy_database_uri: str
        test_plaid_url: str
        test_plaid_client_id: str
        plaid_secret: str
settings: Settings | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global Session
    global settings
    load_dotenv()
    settings = Settings()
    async_database_engine = create_async_engine(settings.async_sqlalchemy_database_uri)
    Session = sessionmaker(bind=async_database_engine, class_=AsyncSession, expire_on_commit=False)
    yield
    await async_database_engine.dispose()
    

app = FastAPI(lifespan=lifespan)

async def yield_db():
    async with Session() as session:
        yield session

def generate_random_id():
    ascii_letters = string.ascii_letters
    numbers = string.digits
    choices = ascii_letters + numbers
    uuid = ''.join([secrets.choice(choices) for _ in range(Constants.IDSizes.SMALL)])
    return uuid


'''
    HELPER UTILITY FUNCTIONS
        env_info
        refresh_database
'''
@app.get('/env_info')
def env_info():
    return {
        "sqlalchemy_database_uri": settings.sqlalchemy_database_uri,
        "test_plaid_url": settings.test_plaid_url,
        "test_plaid_client_id": settings.test_plaid_client_id,
        "plaid_secret": settings.plaid_secret
    }

@app.get('/refresh_database')
def refresh_database(dbsess: AsyncSession = Depends(yield_db)):
    temp_engine = create_engine(settings.sqlalchemy_database_uri)
    Base.metadata.drop_all(temp_engine)
    Base.metadata.create_all(temp_engine)
    temp_engine.dispose()
    return 'Database is refreshed!'

'''
    BATCH SCRIPTS: 'simulate' processing batch scripts


'''
class PlaidBalance(BaseModel):
    available: float
    current: float
    iso_currency_code: str
    limit: Optional[str | None]
    unofficial_currency_code: Optional[str | None]

class PlaidAccount(BaseModel):
    account_id: str
    balances: PlaidBalance
    mask: str
    name: str
    official_name: str
    persistent_account_id: str
    subtype: str
    type: str

@app.get('/batch/refresh_user_data')
async def refresh_user_data(dbsess: AsyncSession = Depends(yield_db)):
    smt = select(User.user_id, User.access_key)
    users = await dbsess.execute(smt)
    users = users.all()
    print(users)

    for uuid, access_key in users:
        # update the account data
        async with httpx.AsyncClient() as client:
            client: httpx.AsyncClient
            resp = await client.post(
                f'{settings.test_plaid_url}/auth/get',
                headers={'Content-Type':'application/json'},
                json={
                    'client_id': settings.test_plaid_client_id,
                    'secret': settings.plaid_secret,
                    'access_token': access_key
                }
            )
            resp = resp.json()
            print(resp, 'is the response')

            accounts = [PAccount(**data) for data in resp['accounts']]


'''
    CLIENT SIDE API
        create_account
        link_account
        get_transactions

'''
class CreateAccountRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    user_email: str
    user_profile_picture: Optional[str]

@app.post('/create_account')
async def create_account(request: CreateAccountRequest, dbsess: AsyncSession = Depends(yield_db)):

    uuid = generate_random_id()
    print('generated a random uuid', uuid)

    while (await dbsess.get(User, uuid)):
        uuid = generate_random_id()

    new_user = User(
        user_id=uuid,
        created_at=datetime.now(),
        last_login_at=datetime.now(),
        access_key=None,
        user_first_name=request.first_name,
        user_last_name=request.last_name,
        user_email=request.user_email,
        user_profile_picture=request.user_profile_picture
    )

    dbsess.add(new_user)

    try:
        await dbsess.commit()
    except Exception as e:
        await dbsess.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="Failed to create account") from e
    
    return {
        'message': 'success',
        'data': {
            'uuid': uuid
        }
    }


class GetPublicTokenRequest(BaseModel):
    uuid: str

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

@app.post('/get_public_token')
async def get_public_token(request: GetPublicTokenRequest):
    public_token = await get_public_token(request.uuid)
    return {
        'public_token': public_token
    }

class LinkAccountRequest(BaseModel):
    uuid: str
    public_token: str

async def plaid_link_account(uuid, public_token):
    for dbsess in yield_db():
        with dbsess.begin():
            access_token = None
            cur_user = dbsess.get(User, uuid)
            if not cur_user:
                raise HTTPException(status_code=500, detail='User with UUID Does Not Exist!')
            
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
                cur_user.access_key = access_token
                await dbsess.commit()
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail='Database Commit Failed!')

@app.post('/link_account')
async def link_account(request: LinkAccountRequest):
    await plaid_link_account(request.uuid)
    return {'message': 'success'}


class GetTransactionsRequest(BaseModel):
    access_token: str
@app.post('/get_transactions')
async def get_transactions():
    pass