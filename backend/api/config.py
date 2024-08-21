import os
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
    test_plaid_url: str
    test_plaid_client_id: str
    plaid_secret: str
    auth_secret_key: str
settings = Settings()

async_database_engine = create_async_engine(settings.async_sqlalchemy_database_uri)
Session = sessionmaker(bind=async_database_engine, class_=AsyncSession, expire_on_commit=False)

async def yield_db():
    async with Session() as session:
        yield session