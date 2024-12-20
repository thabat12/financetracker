from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


from db.models import *
from api.routes.auth import auth_router
from api.routes.plaid import plaid_router
from api.routes.data import data_router
from api.config import settings
from api.config import set_global_session


def bind_paths(app: FastAPI):
    app.include_router(auth_router, prefix='/auth')
    app.include_router(plaid_router, prefix='/plaid')
    app.include_router(data_router, prefix='/data')

def api_add_middleware(app: FastAPI, allowed_origins: list = ["http://localhost", "http://localhost:3000"]):
    app.add_middleware(
        CORSMiddleware,
        allow_origins= allowed_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )

@asynccontextmanager
async def api_app_lifespan(app: FastAPI):
    # set up the session for context manager
    async_database_engine = create_async_engine(settings.async_sqlalchemy_database_uri)
    # sessionmaker is a session factory, yielding a new session on each call
    Session = sessionmaker(bind=async_database_engine, class_=AsyncSession, expire_on_commit=False)
    set_global_session(Session)
    bind_paths(app)
    yield
    await async_database_engine.dispose()

@asynccontextmanager
async def test_api_app_lifespan(app: FastAPI):
    # set up the session for context manager
    async_database_engine = create_async_engine(settings.async_sqlalchemy_database_uri)
    # sessionmaker is a session factory, yielding a new session on each call
    Session = sessionmaker(bind=async_database_engine, class_=AsyncSession, expire_on_commit=False)
    set_global_session(Session)
    bind_paths(app)

    """
        Because programmatic tests != manual tests (with the nice Google login page UI), must override this
        to automatically create a new mock Google user to test with.
    """
    from tests.config import override_google_login_response_dependency
    from api.routes.auth import load_google_login_response_dependency
    app.dependency_overrides[load_google_login_response_dependency] = override_google_login_response_dependency
    yield
    await async_database_engine.dispose()
    app.dependency_overrides.clear()

api_app = FastAPI(lifespan=api_app_lifespan)
test_app = FastAPI(lifespan=test_api_app_lifespan)
api_add_middleware(api_app)
api_add_middleware(test_app)

@api_app.get("/")
def read_root():
    return "Hello World, this is the actual API."

@test_app.get("/")
def read_root():
    return "Hello World, this is the test API."