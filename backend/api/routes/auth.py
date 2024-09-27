from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import *
from api.config import logger, yield_db, yield_client
from api.api_utils.auth_util import LoginGoogleRequest, LoginGoogleResponse, LoginGoogleReturn, GoogleAuthUserInfo
from api.api_utils.auth_util import load_google_login_response, login_google_db_operation, create_auth_session


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

# LOAD: load google auth user info data
async def load_google_login_response_dependency(request: LoginGoogleRequest, client=Depends(yield_client)) -> GoogleAuthUserInfo:
    user_info = await load_google_login_response(request=request, client=client)
    return user_info

# PROCESS: all the database modification in one dependency and one single session
async def login_google_db_operation_dependency(user_info: GoogleAuthUserInfo = Depends(load_google_login_response_dependency),
                                               session = Depends(yield_db)) -> LoginGoogleReturn:
    result: LoginGoogleReturn = await login_google_db_operation(user_info=user_info, session=session)
    return result

# PROCESS: modify the auth session as a separate database operation
async def create_auth_session_dependency(google_login_user_id: LoginGoogleReturn = Depends(login_google_db_operation_dependency), 
                                         session: AsyncSession = Depends(yield_db)) -> LoginGoogleResponse:
    auth_token = await create_auth_session(user_id=google_login_user_id.user_id, session=session)
    
    return LoginGoogleResponse(
        authorization_token=auth_token,
        user_id=google_login_user_id.user_id,
        account_status=google_login_user_id.message
    )

# SEND: the endpoint is only bothered with returning results, and nothing else
@auth_router.post('/login_google')
async def login_google(google_auth_user_info: LoginGoogleResponse = Depends(create_auth_session_dependency)) -> LoginGoogleResponse:
    logger.info('auth/login_google')
    
    return google_auth_user_info