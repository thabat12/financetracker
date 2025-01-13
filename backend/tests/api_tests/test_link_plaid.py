'''
    Run some tests to investigate concurrency and logic updates of the api. These tests are only
    focusing on the client-side interface of the API and are subject to change depending on the
    behavior of the API.
'''
import asyncio
import time
import random
import pytest
import httpx
import requests
import logging
from pydantic import BaseModel
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from settings import settings
from db.models import *
from tests.data.institutiondata import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__).setLevel(logging.INFO)

TEST_API_URL = f"http://{settings.api_hostname}:{settings.api_port}"


class CreateGoogleResponse(BaseModel):
    authorization_token: str
    user_id: str
    account_status: str

class LinkPlaidAccountResponse(BaseModel):
    message: str

def create_mock_google_user_endpoint() -> CreateGoogleResponse:
    resp = requests.post(f"{TEST_API_URL}/auth/create_google", json={})
    return CreateGoogleResponse.model_validate(resp.json())

def link_plaid_account(authorization_token: str, ins_id: str, waitfor: bool = False):
    resp = requests.post(f"{TEST_API_URL}/plaid/link_account", 
                        headers={
                            "Authorization": f"Bearer {authorization_token}",
                            "Content-Type": "application/json"
                        }, 
                        json={"institution_id": ins_id, "waitfor": waitfor},
                        timeout=30)
    
    return LinkPlaidAccountResponse.model_validate(resp.json())

# use this to manually validate any institution after linking account
sql_engine = create_engine(settings.sqlalchemy_database_uri)

"""
    Synchronous testing of the link_plaid endpoint
"""
def test_api_root():
    resp = requests.get(TEST_API_URL)
    assert resp.status_code == 200

# TODO: there is an issue when you make waitfor = False in the api, but I will fix this issue later
def test_link_1_plaid_account(clear_database):
    """
        ensure:
            institution details are populated
            access key is updated to expected values
    """
    # first create the google user
    created_user: CreateGoogleResponse = create_mock_google_user_endpoint()
    authorization_token = created_user.authorization_token
    assert len(authorization_token) > 0
    assert created_user.user_id is not "" and created_user.user_id is not None
    assert created_user.account_status == "created"

    # now link the plaid account
    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.plaid_bank, waitfor=True)

    assert created_link.message == "success"

    with sql_engine.connect() as connection:
        # when a plaid account is linked, you have the side-effect of knowing things about
        # its institution
        smt = select(Institution).where(Institution.institution_id == InstitutionIDs.plaid_bank)
        institution = connection.execute(smt).all()
        assert len(institution) == 1
        
        plaid_bank_institution = institution[0]
        validate_institution(plaid_bank_institution)

        # you should also expect that there is an acces key for this current user
        smt = select(AccessKey).where(AccessKey.user_id == created_user.user_id)
        access_keys = connection.execute(smt).all()
        assert len(access_keys) == 1 # there should only be one of these for the user
        user_access_key = access_keys[0]
        print(user_access_key)

        # validate the access key assuming that there is no need to check for updated time (this process should
        #   still be running asynchronously in the background!)
        validate_access_key(access_key=user_access_key, institution=plaid_bank_institution, updated_time=None)

def test_link_multiple_institutions_to_one_account(clear_database):
    created_user: CreateGoogleResponse = create_mock_google_user_endpoint()
    authorization_token = created_user.authorization_token

    # link multiple accounts sequentially
    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.plaid_bank)
    
    assert created_link.message == "success"

    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.first_platypus_bank)
    
    assert created_link.message == "success"

    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.houndstooth_bank)
    
    assert created_link.message == "success"

    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.pnc)

    assert created_link.message == "success"

    # cheeck and see if all institutions are set
    
    with sql_engine.connect() as conn:
        smt = select(Institution)
        all_institutions = conn.execute(smt).all()
        print("are there 4 institutions connected to the actual database?", all_institutions)
        assert len(all_institutions) == 4

        print("now we are validating the institutions")
        for ins in all_institutions:
            validate_institution(ins)

        print("are there 4 access keys connected to the actual database?")
        smt = select(AccessKey)
        all_access_keys = conn.execute(smt).all()
        assert len(all_access_keys) == 4
        

        # now, let us wait for a bit and let the updates propagate, this might take a while...
        TIMEOUT = 30

        time.sleep(TIMEOUT)

        # i linked only 4 institutions, so there should be 4 institutions associated with transactions
        print("are tehre 4 institutions associated with transactions?")
        smt = text("SELECT COUNT(DISTINCT institution_id) FROM transaction;")
        num_institutions_on_transaction = conn.execute(smt).scalar()
        num_institutions_on_transaction = int(num_institutions_on_transaction)
        assert num_institutions_on_transaction == 4

        # similarly, there should be 4 institutions associated with accounts
        print("are there 4 institutions associated with accounts?")
        smt = text("SELECT COUNT(DISTINCT institution_id) FROM account;")
        num_institutions_on_account = conn.execute(smt).scalar()
        num_institutions_on_account = int(num_institutions_on_account)
        assert num_institutions_on_account == 4  

def test_link_1_investment_account_sync(clear_database):
    created_user: CreateGoogleResponse = create_mock_google_user_endpoint()
    authorization_token = created_user.authorization_token

    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token, InstitutionIDs.pnc, True)
    
    assert created_link.message == "success"

"""
    Asynchronous testing of the link_plaid endpoint
"""

@pytest.mark.asyncio
async def test_link_1_plaid_account_async(clear_database):
    """
        Yeah, this method does not need to be async but whatever
    """
    SLEEP_TIMEOUT = 15

    created_user: CreateGoogleResponse = create_mock_google_user_endpoint()
    assert created_user.authorization_token is not None

    authorization_token = created_user.authorization_token

    # now link the plaid account
    print("about to link the plaid account")
    created_link: LinkPlaidAccountResponse = \
        link_plaid_account(authorization_token=authorization_token, ins_id=InstitutionIDs.plaid_bank)

    print("i just linked the plaid account yay")
    assert created_link.message == "success"

    await asyncio.sleep(SLEEP_TIMEOUT)

    async_engine = create_async_engine(settings.async_sqlalchemy_database_uri)

    async with async_engine.connect() as conn:
        smt = select(Institution).where(Institution.institution_id == InstitutionIDs.plaid_bank)
        institutions = await conn.execute(smt)
        institutions = institutions.all()
        print(institutions, 'is the institution data')
        assert len(institutions) == 1
        institution = institutions[0] # actually get the institution here

        smt = select(AccessKey).where(AccessKey.user_id == created_user.user_id)
        access_keys = await conn.execute(smt)
        access_keys = access_keys.all()
        print(access_keys, 'is the access key data')
        assert len(access_keys) == 1 # there should only be one of these for the user
        user_access_key = access_keys[0]

        # by now, there should be some valid stuff under the access key, and the key should be updated
        validate_access_key(access_key=user_access_key, institution=institution, updated_time=datetime.now())

def async_link_plaid_account_endpoint(async_client: httpx.AsyncClient, authorization_token: str, ins_id: str):
    return async_client.post(f"{TEST_API_URL}/plaid/link_account", headers={
                            "Authorization": f"Bearer {authorization_token}",
                            "Content-Type": "application/json"
                        },
                        json={"institution_id": ins_id})

@pytest.mark.asyncio
async def test_link_5_plaid_accounts_async(clear_database):
    """
        Plaid link account has some limitations in sandbox, and that is especially true when you are
        experiencing rate throttling. So we can't really abuse the concurrency tests due to those exeternal
        issues, but we can assume that our background tasks and everything is working at a somewhat-expected 
        level.
    """
    READ_TIMEOUT = 60
    USERS = 5

    created_users = [create_mock_google_user_endpoint() for _ in range(USERS)]
    ins_choices = [InstitutionIDs.plaid_bank, InstitutionIDs.first_platypus_bank, InstitutionIDs.tartan_dominion, InstitutionIDs.pnc, InstitutionIDs.houndstooth_bank]

    async with httpx.AsyncClient(timeout=READ_TIMEOUT) as client:
        tasks = [async_link_plaid_account_endpoint(client, user.authorization_token, random.choice(ins_choices)) for user in created_users]
        results = await asyncio.gather(*tasks)
        results = [r.json() for r in results]

        print(results, "are the results")

        results = list(map(lambda i: LinkPlaidAccountResponse.model_validate(i), results))

        for r in results:
            assert r.message == "success"
