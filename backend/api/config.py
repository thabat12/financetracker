import os
import httpx
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    async_sqlalchemy_database_uri: str
    sqlalchemy_database_uri: str
    test_async_sqlalchemy_database_uri: str
    test_sqlalchemy_database_uri: str
    test_plaid_url: str
    test_plaid_client_id: str
    plaid_secret: str
    auth_secret_key: str
    api_host: str
    api_port: int
    test_api_host: str
    test_api_port: int
settings = Settings()

# yield_db
global_session = None
session_set = False

def set_global_session(new_global_session):
    global session_set
    if session_set:
        raise Exception('cannot change global_session during runtime!')
    global global_session
    global_session = new_global_session
    session_set = True

async def yield_db():
    global global_session
    if not global_session:
        raise Exception('there is no global session defined!')
    else:
        async with global_session() as session:
            yield session

async def yield_client():
    async with httpx.AsyncClient(timeout=30) as client:
        yield client