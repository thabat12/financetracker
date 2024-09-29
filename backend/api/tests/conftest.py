import os
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from api.crypto.crypto import encrypt_data, encrypt_float, encrypt_integer
import pytest
import random
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.models import *

from api.api import app
from api.tests.config import engine, user_data, TestSession, testapp, override_yield_db
from api.crypto.crypto import db_key_bytes
from api.api_utils.auth_util import GoogleAuthUserInfo


from api.routes.auth import load_google_login_response_dependency

async def initialize_data(session):

    choices = string.ascii_letters + string.digits
    N = len(choices)

    # new user data
    new_users = [
        User(
            user_id=id,
            is_verified=True,
            created_at=True,
            last_login_at=datetime.now(),
            user_first_name=''.join([choices[random.randint(0, N - 1)] for _ in range(20)]),
            user_last_name=''.join([choices[random.randint(0, N - 1)] for _ in range(20)]),
            user_email=''.join([choices[random.randint(0, N - 1)] for _ in range(20)]),
            user_profile_picture='NA',
            user_type='google',
            user_key=encrypt_data(key, db_key_bytes)
        ) for id, key in user_data.items()
    ]


def override_load_google_login_response_dependency(google_auth_user_info: GoogleAuthUserInfo):
    def override():
        return google_auth_user_info
    
    return override


@pytest.fixture(scope='session', autouse=True)
async def setup_test_environment():
    # change the lifecycle context manager to point to new local DB
    # first, set up the global session
    app.dependency_overrides[load_google_login_response_dependency] = override_load_google_login_response_dependency
    

    # bypass the google signin stuff by directly adding users to the database
    await initialize_data()
    
    yield


'''
    TODO: rather than managing my own sessions i will use the Depends dependency
        injection provided by fastapi to do the logic for inserting dependencies.

        then, i will override the dependency in the testing environment as such
            app.dependency_overrides[yield_db] = overriden_yield_db

        this overriden dependency will have the local sqlite database rather than
        the original database, so it will be more modular.

        for increased modularity, i will also create the test suite to entirely
        bypass google auth. in this way, when creating testcases i can simply

        so now, the api is able to run with the database it interacts with set
        and does not require google oauth.

        for the plaid api connections, i would need to manually call the api
        endpoints for each user and populate the tables accordingly. then, i
        will call the endpoints for get accounts, get transactions, and get
        investments. the test will figure out how the api manages concurrency
        with locking and whether the logic is correct.

        estimated time for completion is around 2 weeks.


        testclient = TestClient(app)





'''
