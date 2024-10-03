import os
from fastapi.testclient import TestClient
from api.api import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from api.crypto.crypto import encrypt_data, encrypt_float, encrypt_integer
from api.tests.data.userdata import generate_random_mock_google_user

from api.config import settings

# DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
DATABASE_URL = settings.test_async_sqlalchemy_database_uri
TESTCLIENT_BASE_URL = 'http://test'
async_engine = create_async_engine(DATABASE_URL, pool_size=100, pool_timeout=30)
TestSession = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

# key: user_key
user_data = {
    '1': bytes('abcd', encoding='utf-8'),
    '2': bytes('efgh', encoding='utf-8'),
    '3': bytes('ijkl', encoding='utf-8')
}

# it's the same thing but given a different name
async def override_yield_db():
    async with TestSession() as session:
        try:
            yield session
        finally:
            await session.close()

def override_google_login_response_dependency():
    return generate_random_mock_google_user() # creates a random GoogleAuthUserInfo object