'''
    Run some tests to investigate concurrency and logic updates of the api. These tests are only
    focusing on the client-side interface of the API and are subject to change depending on the
    behavior of the API.
'''
import sys
import asyncio
import pytest
import httpx
import requests
import logging
from dotenv import load_dotenv
from pydantic import BaseModel

from settings import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__).setLevel(logging.INFO)

TEST_API_URL = f'http://{settings.api_hostname}:{settings.api_port}'

class CreateGoogleResponse(BaseModel):
    authorization_token: str
    user_id: str
    account_status: str

def create_mock_google_user_endpoint() -> CreateGoogleResponse:
    resp = requests.post(f"{TEST_API_URL}/auth/create_google", json={})
    return CreateGoogleResponse.model_validate(resp.json())

"""
    Synchronous testing of the google login API
"""
def test_api_root():
    resp = requests.get(f"{TEST_API_URL}", json={})

    assert resp.status_code == 200

def test_create_mock_google_user():
    created_user: CreateGoogleResponse = create_mock_google_user_endpoint()

    authorization_token = created_user.authorization_token
    
    assert len(authorization_token) > 0
    assert created_user.user_id is not "" and created_user.user_id is not None
    assert created_user.account_status == "created"

@pytest.mark.skip
def test_create_mock_google_users_20_sequential():
    """
        Sequential logins take a very long time, so it is better to just test these at
        a lower number (so things aren't as suspenseful)
    """
    N = 20
    for _ in range(N):
        created_user: CreateGoogleResponse = create_mock_google_user_endpoint()
        authorization_token = created_user.authorization_token

        assert len(authorization_token) > 0
        assert created_user.user_id is not "" and created_user.user_id is not None
        assert created_user.account_status == "created"

"""
    Asynchronous testing of the google login API
"""
def async_create_mock_google_user_endpoint(async_client: httpx.AsyncClient):
    return async_client.post(f"{TEST_API_URL}/auth/create_google", json={})

@pytest.mark.asyncio
async def test_google_single_user_100_concurrent_logins():
    """
        This should be relatively fast because FastAPI is designed to be asynchronous
    """
    N = 100

    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [async_create_mock_google_user_endpoint(client) for _ in range(N)]

        # perform these tasks now
        login_results = await asyncio.gather(*tasks)
        login_results = list(map(lambda i: i.json(), login_results))

    assert len(login_results) == N

    for login_result in login_results:
        created_user = CreateGoogleResponse.model_validate(login_result)

        authorization_token = created_user.authorization_token
        assert len(authorization_token) > 0
        assert created_user.user_id is not "" and created_user.user_id is not None
        assert created_user.account_status == "created"