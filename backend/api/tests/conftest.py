import httpx
import asyncio
import pytest
import threading
from fastapi import BackgroundTasks, Depends
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
from api.config import yield_client
from api.tests.config import async_engine, DATABASE_URL, override_google_login_response_dependency
from api.routes.auth import load_google_login_response_dependency
from api.routes.auth import create_auth_session_dependency

from api.api_utils.auth_util import LoginGoogleResponse
from api.api_utils.data_util import db_update_all_data_asynchronously

# shared
async_engine = create_async_engine(DATABASE_URL, pool_size=100, pool_timeout=30)


@pytest.fixture(scope='function')
async def setup_test_environment_fixture():
    '''
        For every test environment, you cannot really use real Google accounts to test for user
        interactions with the API, so that must be changed to a mock user model. 

        Endpoints that indirectly calls the `db_update_all_data_asynchronously` function must run the
        functions synchronously because pytest will not re-use the same asyncio event loop.
    '''

    # creating an entirely new async engine binded to the new event loop
    TestSession = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_yield_db():
        async with TestSession() as session:
            yield session
            await session.commit()
    
    
    # Override dependencies
    app.dependency_overrides[yield_db] = override_yield_db
    app.dependency_overrides[load_google_login_response_dependency] = override_google_login_response_dependency
    # only specific to the auth endpoint
    from api.routes.auth import db_update_all_data_asynchronously_dependency

    # synchronously update the user's data -- test if logic is correct
    async def override_db_update_all_data_asynchronously_dependency(
        google_auth_user_info: LoginGoogleResponse = Depends(create_auth_session_dependency),
        session: AsyncSession = Depends(yield_db),
        client: httpx.AsyncClient = Depends(yield_client)
    ):
        '''
            Shared across multiple test environments, this dependency ensures that data is updated
            synchronously to api calls. This ensures that the asyncio context is the same for every api
            call made to the data util function.
        '''
        await db_update_all_data_asynchronously(google_auth_user_info.user_id, session, client)

    app.dependency_overrides[db_update_all_data_asynchronously_dependency] = override_db_update_all_data_asynchronously_dependency

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

@pytest.fixture(scope='function')
async def link_plaid_environment_fixture():
    '''
        Ensure that the link plaid endpoint also updates the user data synchronously to prevent any
        asyncio context being lost during operation.
    '''

    from api.routes.plaid import db_update_all_data_asynchronously_dependency
    from api.routes.plaid import db_update_user_access_key_dependency
    from api.routes.plaid import verify_token

    async def override_db_update_all_data_asynchronously_dependency(
        background_tasks: BackgroundTasks,
        session: AsyncSession = Depends(yield_db),
        client: httpx.AsyncClient = Depends(yield_client),
        cur_user: str = Depends(verify_token),
        _ = Depends(db_update_user_access_key_dependency)) -> None:
        '''
            On every link account operation, there is a guarantee that the access token does not
            have any data initialized yet. So it is safe to assume that an update is necessary for
            the access key.
        '''
        background_tasks.add_task(db_update_all_data_asynchronously, cur_user, session, client)

    app.dependency_overrides[db_update_all_data_asynchronously_dependency] = override_db_update_all_data_asynchronously_dependency