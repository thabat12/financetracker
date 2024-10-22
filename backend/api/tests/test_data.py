'''
    I am developing test_data as I am working on the data endpoints in Plaid. With this test case
    suite, testing should be much faster and not dependent on UI based workflows any longer. This
    is a lot better of an alternative to a UI based approach and the amount of effort to finally
    move things around in this project is very worth it.
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

