import os
import httpx
from fastapi import HTTPException, Depends, Header
from sqlalchemy import select, delete, asc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import uuid
import hmac
import hashlib
from enum import Enum
from datetime import datetime, timedelta
import string
import secrets

from db.models import *
from api.config import settings, logger, yield_db
from api.crypto.crypto import encrypt_data, decrypt_data, db_key_bytes

'''
    Constants: global variables that affect certain behaviors of functions that modify the database,
        and dictate user-app interactions

'''
SECRET_KEY = bytes(settings.auth_secret_key, encoding='utf-8')
# number of auth sessions at once a user can have
SESSION_LIMIT = 3
GOOGLE_AUTH_USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'


'''
    Models: all the useful models that the API uses to parse and return responses to the client


'''
class CreateAccountRequest(BaseModel):
    user_type: str
    first_name: str
    last_name: str
    user_email: str
    user_profile_picture: Optional[str]

class MessageEnum(Enum):
    CREATED = 'created'
    LOGIN = 'login'

class CreateAccountReturn(BaseModel):
    message: MessageEnum
    user_id: str

class LoginGoogleRequest(BaseModel):
    access_token: str

class LoginGoogleReturn(BaseModel):
    message: Optional[MessageEnum] = None
    user_id: Optional[str] = None

class GoogleAuthUserInfo(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    verified_email: Optional[bool] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None

    error: Optional[str] = None
    error_description: Optional[str] = None

class LoginGoogleResponse(BaseModel):
    authorization_token: str
    user_id: str
    account_status: str

'''
    Util Functions: functions that generate user IDs and tokens for authorization sessions

'''

def generate_random_id():
    ascii_letters = string.ascii_letters
    numbers = string.digits
    choices = ascii_letters + numbers
    uuid = ''.join([secrets.choice(choices) for _ in range(Constants.IDSizes.SMALL)])
    return uuid

def generate_token(user_id: str) -> str:
    token_id = str(uuid.uuid4())
    token_data = f"{user_id}:{token_id}"
    signature = hmac.new(SECRET_KEY, token_data.encode(), hashlib.sha256).hexdigest()
    token = f"{token_data}:{signature}"
    
    return token

# verify_token manages its own database session
async def verify_token(authorization: str = Header(...), session: AsyncSession = Depends(yield_db)) -> tuple[bool, str]:
    token = authorization.strip().split(' ')[-1].strip()
    session: AsyncSession
    auth_session: AuthSession = await session.get(AuthSession, token)

    if not auth_session:
        raise HTTPException(status_code=500, detail='auth_session is not provided')
    
    expiry_time = auth_session.session_expiry_time

    if datetime.now() > expiry_time:
        await session.delete(auth_session)
        await session.commit()
        raise HTTPException(status_code=500, detail='auth_session has expired')
    else:
        cur_user = auth_session.user_id

    try:
        token_data, token_signature = token.rsplit(":", 1)
        expected_signature = hmac.new(SECRET_KEY, token_data.encode(), hashlib.sha256).hexdigest()
        result = hmac.compare_digest(expected_signature, token_signature)

        if result:
            return True, cur_user
        else:
            logger.info(f'/plaid/link_account: {cur_user} auth_session is invalid')
            raise HTTPException(f'{cur_user} auth_session is invalid')
    except Exception:
        raise HTTPException(status_code=500, detail='Token data parsing went wrong!')


async def decrypt_user_key(cur_user: str, session: AsyncSession):
    smt = select(User.user_key).where(User.user_id == cur_user)
    user_key: bytes = await session.scalar(smt)
    return decrypt_data(user_key, db_key_bytes)

'''
    Database modification operations: all the database modificiations that change certain states of
        the database. these reflect user logins and updates.


'''

async def create_account(new_user: CreateAccountRequest, link_id: str, session: AsyncSession) -> CreateAccountReturn:
    logger.info('/auth/create_account')
    uuid = generate_random_id()

    new_user = User(
        user_id=uuid,
        is_verified=True,
        created_at=datetime.now(),
        last_login_at=datetime.now(),
        user_first_name=new_user.first_name,
        user_last_name=new_user.last_name,
        user_email=new_user.user_email,
        user_profile_picture=new_user.user_profile_picture,
        user_type=new_user.user_type,
        user_key=encrypt_data(os.urandom(32), db_key_bytes)
    )

    if new_user.user_type == 'google':
        google_user = GoogleUser(google_user_id=link_id, user_id=uuid)

    try:
        session.add(new_user)
        session.add(google_user)
        await session.commit()
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail='Database Operation Failed!') from e
    
    return CreateAccountReturn(message=MessageEnum.CREATED, user_id=uuid)

async def login_google_db_operation(user_info: GoogleAuthUserInfo, session: AsyncSession) -> LoginGoogleReturn:
    logger.info('/auth/login_google_db_operation')
    result: LoginGoogleReturn = LoginGoogleReturn()

    google_user: GoogleUser = await session.get(GoogleUser, user_info.id)
    
    # I have to create the google user
    if not google_user:
        logger.info('/auth/login_google_db_operation: user does not exist, creating account')
        user_name_info = user_info.name.strip().split(' ')
        if len(user_name_info) == 1:
            first_name = user_name_info[0]
            last_name = None
        elif len(user_name_info) > 1:
            first_name, last_name = user_name_info[0], user_name_info[-1]

        create_account_request = CreateAccountRequest(
            first_name=first_name,
            last_name=last_name,
            user_email=user_info.email,
            user_profile_picture=user_info.picture,
            user_type='google'
        )

        response: CreateAccountReturn = await create_account(new_user=create_account_request, link_id=user_info.id, session=session)
        result.message = MessageEnum.CREATED
        result.user_id = response.user_id
    # user already exists so return the state of this user
    else:
        cur_user_id: str = google_user.user_id
        logger.info(f'/auth/login_google_db_operation: {cur_user_id} google user already exists')
        cur_user: User = await session.get(User, cur_user_id)

        cur_user.last_login_at = datetime.now()
        user_id = cur_user.user_id

        await session.commit()

        result.message = MessageEnum.LOGIN
        result.user_id = user_id
    
    return result

async def create_auth_session(user_id: str, session: AsyncSession):
    logger.info('/auth/create_auth_session')
    auth_token = generate_token(user_id=user_id)

    session: AsyncSession
    smt = select(AuthSession.auth_session_token_id).where(AuthSession.user_id == user_id).order_by(asc(AuthSession.session_expiry_time))
    cur_sessions = await session.scalars(smt)
    cur_sessions = cur_sessions.all()

    if cur_sessions:
        if len(cur_sessions) == 3:
            logger.info(f'/auth/create_auth_session: {user_id} deleting oldest auth session')
            to_del_id = cur_sessions[0]

            smt = delete(AuthSession).where(AuthSession.auth_session_token_id == to_del_id)
            await session.execute(smt)
        elif len(cur_sessions) > 3:
            raise Exception('oops! somehow, there are more than 3 sessions on the table for user', user_id)
    
    # after all the corresponding deletes, create the new auth session
    logger.info(f'/auth/create_auth_session: {user_id} creating auth session for')
    auth_session = AuthSession(auth_session_token_id=auth_token, \
        session_expiry_time=datetime.now() + timedelta(minutes=30), user_id=user_id)
    
    session.add(auth_session)
    await session.commit()

    return auth_token

'''
    HTTP client operations: calling the google api requires some httpx context, which is also handled
        apart from the actual fastapi calling logic

'''

async def load_google_login_response(request: LoginGoogleRequest, client: httpx.AsyncClient):
    logger.info(f'auth/login_google: requesting google to validate access token')
    response = await client.get(f'{GOOGLE_AUTH_USERINFO_URL}?access_token={request.access_token}')
    response = response.json()
    user_info = GoogleAuthUserInfo.model_validate(response)

    if user_info.error is not None:
        logger.error('auth/login_google: invalid access token provided')
        raise HTTPException(status_code=401, detail='Access Token Provided is Invalid!')
    
    return user_info