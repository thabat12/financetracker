
import httpx
import secrets
import string
from datetime import datetime
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, delete, create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import asyncio


from db.models import *
from api.routes.auth import auth_router
from api.routes.plaid import plaid_router
from api.routes.data import data_router
from api.config import async_database_engine
from api.config import settings
from api.config import yield_db
from api.config import set_global_session
from api.config import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # set up the session for context manager
    set_global_session(Session)
    app.include_router(auth_router, prefix='/auth')
    app.include_router(plaid_router, prefix='/plaid')
    app.include_router(data_router, prefix='/data')
    yield
    await async_database_engine.dispose()
    
app = FastAPI(lifespan=lifespan)

allowed_origins = ["http://localhost", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

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
def refresh_database():
    temp_engine = create_engine(settings.sqlalchemy_database_uri)
    Base.metadata.drop_all(temp_engine)
    Base.metadata.create_all(temp_engine)
    temp_engine.dispose()
    return 'Database is refreshed!'


async def get_institution_by_id(id: str):
    data = None

    async with httpx.AsyncClient() as client:
        data = await client.post(f'{settings.test_plaid_url}/institutions/get_by_id',
                                 headers={
                                     'Content-Type': 'application/json'
                                 },
                                 json={
                                     'institution_id': id,
                                     'country_codes': ['US'],
                                     'client_id': settings.test_plaid_client_id,
                                     'secret': settings.plaid_secret
                                 })
        
        data = data.json()

    return data


@app.get('/institution_data')
async def institution_data(data_type: Optional[str] = 'transactions', limit: Optional[int] = 500, offset: Optional[int] = 0):
    
    async with httpx.AsyncClient() as client:
        if data_type == 'investments':
            institutions_supported = ['ins_13', 'ins_109508']
            tasks = [asyncio.create_task(get_institution_by_id(cur_institution)) for cur_institution in institutions_supported]
            data = {
                'institutions': []
            }
            for result in await asyncio.gather(*tasks):
                data['institutions'].append(result['institution'])
        else:
            data = await client.post(f'{settings.test_plaid_url}/institutions/get', 
                            headers= {
                                'Content-Type': 'application/json'
                            },
                            json= {
                                'client_id': settings.test_plaid_client_id,
                                'secret': settings.plaid_secret,
                                'count': limit,
                                'offset': offset,
                                'country_codes': ['US'],
                                'options': {
                                    'products': [data_type]
                                }
                            })
            data = data.json()

    return data