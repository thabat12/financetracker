import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from db.models import *
from db.models import Base

from api.api import app
from api.config import settings
from api.config import yield_db
from api.tests.config import override_yield_db, override_google_login_response_dependency, engine
from api.routes.auth import load_google_login_response_dependency

@pytest.fixture(scope='function')
async def setup_test_environment_fixture():
    # Override dependencies
    app.dependency_overrides[yield_db] = override_yield_db
    app.dependency_overrides[load_google_login_response_dependency] = override_google_login_response_dependency

    # Create tables in the database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print('Database table setup is complete!')

    yield True


    print('Closing up the database connection now!')
    # Cleanup can also be done here if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)