import os
from fastapi.testclient import TestClient
from api.api import app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from api.crypto.crypto import encrypt_data, encrypt_float, encrypt_integer

DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
engine = create_async_engine(DATABASE_URL)
TestSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# key: user_key
user_data = {
    '1': bytes('abcd', encoding='utf-8'),
    '2': bytes('efgh', encoding='utf-8'),
    '3': bytes('ijkl', encoding='utf-8')
}

# it's the same thing but given a different name
testapp = app

async def override_yield_db():
    async with TestSession as session:
        yield session