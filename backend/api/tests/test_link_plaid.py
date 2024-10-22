'''
    These suite of tests will ensure that all the Plaid level stuff is
    handled properly.
'''
import sys
import time
import asyncio
import pytest
import httpx
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import ASGITransport
from sqlalchemy import select
import logging


from api.api import app
from api.tests.data.userdata import generate_random_mock_google_user
from api.api_utils.auth_util import GoogleAuthUserInfo, MessageEnum
from api.routes.auth import auth_router, load_google_login_response_dependency
from api.routes.plaid import plaid_router
from api.tests.config import override_yield_db, TESTCLIENT_BASE_URL, async_engine
from api.tests.conftest import logger
from api.tests.data.userdata import PLAID_SANDBOX_INSTITUTION_IDS
from db.models import *

# client = TestClient(app=app)
app.include_router(auth_router, prefix='/auth')
app.include_router(plaid_router, prefix='/plaid')

# helper function to create the httpx tasks
def client_task(authorization_token: str, ins_id: str, client: httpx.AsyncClient):
    return client.post(f'{TESTCLIENT_BASE_URL}/plaid/link_account', 
                        headers={
                            "Authorization": f'Bearer {authorization_token}',
                            "Content-Type": "application/json"
                        },
                        json={'institution_id': ins_id})

class InstitutionIDs:
    plaid_bank = 'ins_109508' # transactions & investments
    first_platypus_bank = 'ins_109510' # transactions
    tartan_bank = 'ins_109512' # transactions & investments
    pnc = 'ins_13' # transactions & investments

# @pytest.mark.skip
@pytest.mark.asyncio
async def test_link_1_transaction_account(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            # first get some users onto the database
            result = await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            result = result.json()
            print(result)
            authorization_token = result['authorization_token']


            result = await client_task(authorization_token=authorization_token, \
                                       ins_id=InstitutionIDs.plaid_bank, client=client)
            
            result = result.json()
            print(result)

# @pytest.mark.skip
@pytest.mark.asyncio
async def test_link_multiple_accounts_to_same_institution(setup_test_environment_fixture):
    async for _ in setup_test_environment_fixture:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            result = await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            result = result.json()
            authorization_token = result['authorization_token']

            start = time.time()

            result = await client_task(authorization_token=authorization_token, \
                                        ins_id=InstitutionIDs.plaid_bank, client=client)
            
            end = time.time()

            result = result.json()

            # very lax requirement of within 15 seconds
            assert end - start <= 15
            assert result['message'] == 'success'

            # now test with N = 10 other clients on the same institution
            N = 10
            clients = await asyncio.gather(*[client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={}) for _ in range(N)])
            clients = [c.json() for c in clients]
            authorization_tokens = [c['authorization_token'] for c in clients]
            requests = [client_task(authorization_token=token, ins_id=InstitutionIDs.plaid_bank, client=client) \
                        for token in authorization_tokens]
            
            start = time.time()
            results = await asyncio.gather(*requests)
            end = time.time()

            results = [r.json() for r in results]

            assert all([i['message'] == 'success' for i in results])

@pytest.mark.asyncio
async def test_link_1_account_to_multiple_institutions(setup_test_environment_fixture):
    print('is this even working?')
    async for _ in setup_test_environment_fixture:
        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=TESTCLIENT_BASE_URL) as client:
            # first login with a user
            response = await client.post(f'{TESTCLIENT_BASE_URL}/auth/create_google', json={})
            response = response.json()
            authorization_token = response['authorization_token']
            user_id = response['user_id']

            requests = [
                client_task(authorization_token=authorization_token, ins_id=InstitutionIDs.plaid_bank, client=client),
                client_task(authorization_token=authorization_token, ins_id=InstitutionIDs.first_platypus_bank, client=client),
                client_task(authorization_token=authorization_token, ins_id=InstitutionIDs.tartan_bank, client=client),
            ]

            responses = await asyncio.gather(*requests)
            responses = [r.json() for r in responses]

            assert all([i['message'] == 'success' for i in responses])

            # also check the database to ensure that each access key is populated correctly
            Session = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

            async with Session() as session:
                async with session.begin():
                    smt = select(AccessKey).where(AccessKey.user_id == user_id)
                    access_keys = await session.execute(smt)
                    access_keys = access_keys.all()

                    # simple test to ensure that there are the expected count of access keys
                    assert len(access_keys) == 3

                    # next check the institution data being populated
                    institutions = await session.execute(select(Institution))
                    institutions = institutions.scalars().all()

                    # very hardcoded checking for institution support on sandbox
                    for ins in institutions:
                        logger.info(ins.__dir__())
                        ins: Institution

                        if ins.institution_id == InstitutionIDs.pnc:
                            assert ins.supports_investments and ins.supports_transactions
                        elif ins.institution_id == InstitutionIDs.plaid_bank:
                            assert ins.supports_investments and ins.supports_transactions
                        elif ins.institution_id == InstitutionIDs.tartan_bank:
                            assert ins.supports_investments and ins.supports_transactions
                        elif ins.institution_id == InstitutionIDs.first_platypus_bank:
                            assert not ins.supports_investments and ins.supports_transactions