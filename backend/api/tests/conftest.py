import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from db.models import *
from db.models import Base

from api.api import app
from api.config import settings
from api.config import yield_db
from api.tests.config import override_google_login_response_dependency, \
                                async_engine, DATABASE_URL, override_yield_db
from api.routes.auth import load_google_login_response_dependency

@pytest.fixture(scope='function')
async def setup_database_fixture():
    engine = create_async_engine(settings.test_async_sqlalchemy_database_uri, pool_size=100, pool_timeout=30)

    # Create tables in the database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()
        await conn.close()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.commit()
        await conn.close()

    await engine.dispose()


@pytest.fixture(scope='session')
async def setup_test_environment_fixture():

    # Override dependencies
    app.dependency_overrides[yield_db] = override_yield_db
    app.dependency_overrides[load_google_login_response_dependency] = override_google_login_response_dependency

    yield True

    print('Closing up the database connection now!')
    # Cleanup can also be done here if needed
    
    # reset to default state for the app
    app.dependency_overrides.clear()


@pytest.fixture
async def setup_pytest_environment_fixture(setup_test_environment_fixture, setup_database_fixture):
    async for _ in setup_test_environment_fixture:
        async for _ in setup_database_fixture:
            yield