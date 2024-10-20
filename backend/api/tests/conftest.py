import asyncio
import pytest
import threading
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from asyncio import Lock
from sqlalchemy import Pool, event
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.propagate = True

from db.models import *
from db.models import Base

from api.api import app
from api.config import settings
from api.config import yield_db
from api.tests.config import async_engine, DATABASE_URL, override_google_login_response_dependency
from api.routes.auth import load_google_login_response_dependency

# shared
async_engine = create_async_engine(DATABASE_URL, pool_size=200, pool_timeout=30)
pool_size_lock = Lock()
pool_size = 0
shared_override_yield_db = None

@pytest.fixture(scope='function')
async def setup_test_environment_fixture():
    # creating an entirely new async engine binded to the new event loop
    TestSession = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_yield_db():
        async with TestSession() as session:
            yield session
            await session.commit()
    
    # allow the testing scripts to access this new depdendency
    shared_override_yield_db = override_yield_db
    
    # Override dependencies
    app.dependency_overrides[yield_db] = override_yield_db
    app.dependency_overrides[load_google_login_response_dependency] = override_google_login_response_dependency

    # database table setup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print('setting up')

    yield True
    
    print('cleaning up')
    # clear all database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()

    # reset to default state for the app
    app.dependency_overrides.clear()