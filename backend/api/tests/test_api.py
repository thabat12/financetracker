'''
    Run some tests to investigate concurrency and logic updates of the api
'''

import asyncio
import concurrent.futures
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import select

from api.api import app
from fastapi.testclient import TestClient
from api.tests.data.userdata import generate_random_mock_google_user
from api.api_utils.auth_util import GoogleAuthUserInfo, MessageEnum
from api.routes.auth import auth_router
from api.routes.plaid import plaid_router
from api.tests.config import override_yield_db, TESTCLIENT_BASE_URL
from api.tests.data.userdata import PLAID_SANDBOX_INSTITUTION_IDS
from db.models import *

# client = TestClient(app=app)
app.include_router(auth_router, prefix='/auth')
app.include_router(plaid_router, prefix='/plaid')

@pytest.mark.asyncio
async def test_google_login(setup_test_environment_fixture):

    # handle async context via async for loop
    async for _ in setup_test_environment_fixture:

        N_USERS = 10
        login_results = None

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            tasks = [client.post(f'{TESTCLIENT_BASE_URL}/auth/login_google', json={}) for _ in range(N_USERS)]

            login_results = await asyncio.gather(*tasks)
            login_results = list(map(lambda i: i.json(), login_results))
            
        assert len(login_results) == N_USERS
        all_created = True
        for result in login_results:
            all_created = all_created & (result['account_status'] == MessageEnum.CREATED.value)
        assert all_created

        async for session in override_yield_db():
            smt = select(GoogleUser)
            all_google_users = await session.execute(smt)
            all_google_users = all_google_users.all()

            assert len(all_google_users) == N_USERS

@pytest.mark.asyncio
async def test_google_multiple_logins(setup_test_environment_fixture):

    async for _ in setup_test_environment_fixture:
        pass

@pytest.mark.asyncio
async def test_plaid_link_flow_one_user(setup_test_environment_fixture):
    
    async for _ in setup_test_environment_fixture:
        
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            response = await client.post(f'{TESTCLIENT_BASE_URL}/auth/login_google', json={})
            response = response.json()

            auth_token = response['authorization_token']
            tasks = []

            for ins_id in PLAID_SANDBOX_INSTITUTION_IDS:
                pass

            print('my auth token', auth_token)