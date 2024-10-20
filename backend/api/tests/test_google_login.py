'''
    Run some tests to investigate concurrency and logic updates of the api. These tests are only
    focusing on the client-side interface of the API and are subject to change depending on the
    behavior of the API.
'''
import sys
import asyncio
import pytest
import httpx
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import ASGITransport
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__).setLevel(logging.INFO)

from api.api import app
from api.tests.data.userdata import generate_random_mock_google_user
from api.api_utils.auth_util import GoogleAuthUserInfo, MessageEnum
from api.routes.auth import auth_router, load_google_login_response_dependency
from api.routes.plaid import plaid_router
from api.tests.config import override_yield_db, TESTCLIENT_BASE_URL, async_engine
from api.tests.data.userdata import PLAID_SANDBOX_INSTITUTION_IDS
from db.models import *


# client = TestClient(app=app)
app.include_router(auth_router, prefix='/auth')
app.include_router(plaid_router, prefix='/plaid')

@pytest.mark.skip
@pytest.mark.asyncio
async def test_one_google_login(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})

@pytest.mark.skip
@pytest.mark.asyncio
async def test_10_concurrent_google_logins(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        # handle async context via async for loop
        N_USERS = 10
        login_results = None

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            tasks = [client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={}) for _ in range(N_USERS)]

            login_results = await asyncio.gather(*tasks)
            login_results = list(map(lambda i: i.json(), login_results))
        assert len(login_results) == N_USERS

@pytest.mark.skip
@pytest.mark.asyncio
async def test_google_login_twice(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        random_user: GoogleAuthUserInfo = generate_random_mock_google_user()
        # keep the login user the same every time
        app.dependency_overrides[load_google_login_response_dependency] = lambda: random_user

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:

            response = await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            response = response.json()
            assert response['account_status'] == 'login'

            response = await client.post(f'{TESTCLIENT_BASE_URL}/auth/login_google', json={})
            response = response.json()
            assert response['account_status'] == 'login'

@pytest.mark.skip
@pytest.mark.asyncio
async def test_google_single_user_100_sequential_logins(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        N = 10
        random_user: GoogleAuthUserInfo = generate_random_mock_google_user()
        google_id = random_user.id
        # keep the login user the same every time
        app.dependency_overrides[load_google_login_response_dependency] = lambda: random_user

        num_created, num_login = 0, 0

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            for _ in range(N):
                result = await client.post(f'{TESTCLIENT_BASE_URL}/auth/login_google', json={})
                result = result.json()

                num_login += int(result['account_status'] == 'login')

        assert num_login == N

# @pytest.mark.skip
@pytest.mark.asyncio
async def test_google_single_user_100_concurrent_logins(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        N = 10

        random_user: GoogleAuthUserInfo = generate_random_mock_google_user()
        google_id = random_user.id
        # keep the login user the same every time
        app.dependency_overrides[load_google_login_response_dependency] = lambda: random_user

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            tasks = [client.post(f'{TESTCLIENT_BASE_URL}/auth/login_google', json={}) for _ in range(N)]
            results = await asyncio.gather(*tasks)
            results = [i.json() for i in results]

        num_created, num_login = 0, 0