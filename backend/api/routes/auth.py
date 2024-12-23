import httpx
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import *
from api.config import logger, yield_db, yield_client
from api.api_utils.auth_util import LoginGoogleRequest, LoginGoogleResponse, LoginGoogleReturn, GoogleAuthUserInfo
from api.api_utils.auth_util import load_google_login_response
from api.api_utils.auth_util import login_google_db_operation
from api.api_utils.auth_util import create_google_db_operation
from api.api_utils.auth_util import create_auth_session
from api.api_utils.data_util import db_update_all_data_asynchronously


'''
    The auth router file only has the view of dependencies and flow of API execution. all the database and
        api calling logic is abstracted away. The view here that is important is the dependency tree. Each
        stage of dependency here can be modified as the following: 

        load_google_login_response_dependency: the actual google user that is logging in may be modified
            (ex. in a testcase, avoid calling the http endpoint for a google user and return the information
                in an object directly)

        login_google_db_operation_dependency: places the a new potential google user information details
            into the database. if the user is not new, then it simply reads current user from the database

        create_auth_session_dependency: creates an authorization token for the user and returns the details
            that are given to by login_google_db_operation_dependency and self to provide the overall
            status of login operation
'''

auth_router = APIRouter()

# CACHED SESSION
async def session_dependency(session=Depends(yield_db)) -> AsyncSession:
    logger.info("session_dependency")
    return session

# LOAD: load google auth user info data
async def load_google_login_response_dependency(
        request: LoginGoogleRequest, 
        client: httpx.AsyncClient = Depends(yield_client)) -> GoogleAuthUserInfo:
    """
        Given some JWT access token, validate that token and extract the associated user settings like
        email, name, google id, etc.
    """
    logger.info("load_google_login_response_dependency")
    user_info = await load_google_login_response(request=request, client=client)
    return user_info

# PROCESS: all the database modification in one dependency and one single session
async def login_google_db_operation_dependency(
        request: Request,
        user_info: GoogleAuthUserInfo = Depends(load_google_login_response_dependency),
        session = Depends(session_dependency)) -> LoginGoogleReturn:
    """
        Both create_google and login_google will eventually call this dependency, which has two different options:
            - create google:
                - creates a new user in the database, given the parameters in the request
                    - this will assign Google account information along with the user_key, user_id
                - log in the user (this just sets the date of last login on the user in the database)
                    - just ensures that you can read the user off of the database

            - login google:
                - ensure you can read the user off of the database and returns that user information
    
    """
    logger.info('auth/login_google_db_operation_dependency')
    path = request.url.path
    if path == '/auth/login_google':
        result = await login_google_db_operation(user_info=user_info, session=session)
    elif path == '/auth/create_google':
        logger.info('creating user')
        await create_google_db_operation(user_info=user_info, session=session)
        result = await login_google_db_operation(user_info=user_info, session=session, is_created=True)
    else:
        raise HTTPException(detail='invalid path provided!', status_code=500)

    logger.info('login google db operation dependency done')
    return result

# PROCESS: modify the auth session as a separate database operation
async def create_auth_session_dependency(
        user_db: LoginGoogleReturn = Depends(login_google_db_operation_dependency),
        session: AsyncSession = Depends(session_dependency)) -> LoginGoogleResponse:
    """
        Given a specific user_id property, create a new authorization session (with the auth token) for
        the current user. Note that this auth session has an expiry time, and is capped at 3 simultaneous
        sessions per user.
    """
    logger.info('/auth/create_auth_session_dependency')
    auth_token = await create_auth_session(user_id=user_db.user_id, session=session)
    logger.info(auth_token)
    return LoginGoogleResponse(
        authorization_token=auth_token,
        user_id=user_db.user_id,
        account_status=user_db.message
    )

# SEND: the endpoint is only bothered with returning results, and nothing else
@auth_router.post('/login_google')
async def login_google(google_auth_user_info: LoginGoogleResponse = Depends(create_auth_session_dependency)) -> LoginGoogleResponse:
    """
        User already exists on the database, re-log in given that user id in the request.
    """
    logger.info('auth/login_google')
    return google_auth_user_info

@auth_router.post('/create_google')
async def create_google(google_auth_user_info: LoginGoogleResponse = Depends(create_auth_session_dependency)) -> LoginGoogleResponse:
    """
        User does not exist on the database, so must create and then log in the user.
    """
    logger.info('auth/create_google')
    logger.info(google_auth_user_info)
    return google_auth_user_info