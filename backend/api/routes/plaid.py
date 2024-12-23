import httpx
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import logger, yield_db, yield_client
from db.models import Institution
from api.api_utils.plaid_util import LinkAccountRequest, LinkAccountResponse, LinkAccountResponseEnum
from api.api_utils.auth_util import verify_token
from api.api_utils.plaid_util import db_update_institution_details, plaid_get_public_token, \
                                    exchange_public_token, update_user_access_key
from api.api_utils.data_util import db_update_all_data_asynchronously


'''
    The plaid router file focuses on defining the view of dependencies and the flow of API execution 
    for linking a user's financial institution account via Plaid. The database and API interaction 
    logic are abstracted away, and the key focus here is the dependency tree. Each stage of dependency 
    can be modified as needed for different use cases, just like the auth.py routes.

    The dependencies are structured in the following way:

        1. verify_token_dependency:
            - Verifies the token of the current user logging in to ensure that the authentication 
                process is successful. This is the leaf of the tree and must be working in order for
                the rest of the logic to propagate in the endpoint call.
            - **Expected Dependencies**: None

        2. db_update_institution_details_dependency:
            - Updates or fetches the financial institution details for the current user. This ensures 
                that the selected institution is up to date in the database. This is important for
                later operations that rely on the institution details to figure out specific product
                categories that need updates.
            - **Expected Dependencies**:
                - `verify_token_dependency`: Ensures the user is authenticated before updating 
                    institution details.
            
        3. plaid_get_public_token_dependency:
            - Retrieves a public token for the user's selected institution using the Plaid API. This 
                token is needed to initiate the account linking process.
            - **Expected Dependencies**:
                - `db_update_institution_details_dependency`: Ensures that institution details are 
                    updated before retrieving the public token. The internal Plaid api call must read
                    off of the supported institutions and the ins_id from this dependency.
                - `verify_token_dependency`: Confirms the user is authenticated.

        4. plaid_exchange_public_token_dependency:
            - Exchanges the public token for an access token using Plaid's token exchange API. The 
                access token is required for subsequent actions on the user's institution account.
            - **Expected Dependencies**:
                - `plaid_get_public_token_dependency`: Ensures that a valid public token has been 
                    obtained before exchanging it for an access token.
                - `verify_token_dependency`: Confirms the user is authenticated.

        5. db_update_user_access_key_dependency:
            - Stores the access token in the database, ensuring that the user's account details and 
                access keys are securely saved and updated.
            - **Expected Dependencies**:
                - `plaid_exchange_public_token_dependency`: Retrieves the access token before 
                    updating the database.
                - `verify_token_dependency`: Ensures the user is authenticated.
                - `db_update_institution_details_dependency`: Confirms that institution details are 
                    current before updating the user's access key.
        
    Each of these dependencies is designed to be modular. For example, in a test case, you could 
    replace `plaid_get_public_token_dependency` to avoid making an actual API call and return a mock 
    token instead. Similarly, `db_update_institution_details_dependency` can be customized to work 
    with test data for specific cases.
'''


plaid_router = APIRouter()

# CACHED SESSION
async def session_dependency(session=Depends(yield_db)) -> AsyncSession:
    logger.info("SESSION DEPENDENCY CREATED NEW SESSION")
    return session

async def verify_token_depdendency(cur_user: tuple[bool, str] = Depends(verify_token)) -> str:
    logger.info(f"verify_token_dependency called for user: {cur_user[1]}")
    return cur_user[1]

async def db_update_institution_details_dependency(
        request: LinkAccountRequest, 
        cur_user: str = Depends(verify_token_depdendency),
        session: AsyncSession = Depends(session_dependency) ) -> Institution:
    
    logger.info(f"db_update_institution_details_dependency called for user: {cur_user}, request: {request}")
    new_ins: Institution = await db_update_institution_details(request=request, session=session)
    return new_ins

async def plaid_get_public_token_dependency(
        request: LinkAccountRequest, # for sandbox purposes, add a custom_user field
        ins_details: Institution = Depends(db_update_institution_details_dependency),
        cur_user: str = Depends(verify_token_depdendency),
        client: httpx.AsyncClient = Depends(yield_client)) -> str:
    
    logger.info(f"plaid_get_public_token_dependency called for user: {cur_user}, institution: {ins_details.name}")
    public_token: str = await plaid_get_public_token(ins_details=ins_details, client=client, custom_user=request.custom_user)
    return public_token

async def plaid_exchange_public_token_dependency(
        public_token: str = Depends(plaid_get_public_token_dependency), 
        cur_user: str = Depends(verify_token_depdendency),
        client: httpx.AsyncClient = Depends(yield_client)) -> LinkAccountResponse:
    '''
        Given the link token, exchange it with the Plaid API to obtain the actual
        public token, which will be set up in the database for the corresponding user.
    '''
    logger.info(f"plaid_exchange_public_token_dependency called for user: {cur_user}, public token: {public_token}")
    access_token = await exchange_public_token(public_token=public_token, client=client)
    return access_token

async def db_update_user_access_key_dependency(
        access_key: str = Depends(plaid_exchange_public_token_dependency), 
        cur_user: str = Depends(verify_token_depdendency),
        ins_details: Institution = Depends(db_update_institution_details_dependency),
        session: AsyncSession = Depends(session_dependency)) -> None:
    '''
        Populate the AccessKey record with the new public token that will be used for
        future API calls.
    '''
    logger.info(f"db_update_user_access_key_dependency called for user: {cur_user}, institution: {ins_details.name}")
    await update_user_access_key(access_key=access_key, cur_user=cur_user, ins_details=ins_details, session=session)

async def db_update_all_data_asynchronously_dependency(
        background_tasks: BackgroundTasks,
        _ = Depends(db_update_user_access_key_dependency),
        cur_user: str = Depends(verify_token_depdendency)) -> None:
    '''
        On every link account operation, there is a guarantee that the access token does not
        have any data initialized yet. So it is safe to assume that an update is necessary for
        the access key.
    '''
    logger.info(f"db_update_all_data_asynchronously_dependency called for user: {cur_user}")
    background_tasks.add_task(db_update_all_data_asynchronously, cur_user)

# Process, Process, Load, Load, Return, (and a special background task to update data asynchronously)
# takes in a LinkAccountRequest model as input
@plaid_router.post('/link_account')
async def link_account(
    # background_tasks: BackgroundTasks,
    _ = Depends(db_update_all_data_asynchronously_dependency), 
    cur_user: str = Depends(verify_token_depdendency)) -> LinkAccountResponse:
    logger.info(f'/plaid/link_account: endpoint for user {cur_user} called')

    # fire off background task
    # background_tasks.add_task(db_update_all_data_asynchronously, cur_user)
    return LinkAccountResponse(message=LinkAccountResponseEnum.SUCCESS)

"""
    temporary test to see if the update asynchronous data is actually working or not
"""

from pydantic import BaseModel

class LinkAccountTestRequest(BaseModel):
    custom_user: str

@plaid_router.post('/link_account_test')
async def link_account_test(
    request: LinkAccountTestRequest,
    background_tasks: BackgroundTasks,
    ):

    background_tasks.add_task(db_update_all_data_asynchronously, request.custom_user)