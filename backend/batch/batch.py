import httpx
import secrets
import string
from datetime import datetime
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select, update, delete, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from batch.config import Config
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

from db.models import *

Session: AsyncSession | None = None
class Settings(BaseSettings):
        async_sqlalchemy_database_uri: str
        sqlalchemy_database_uri: str
        test_plaid_url: str
        test_plaid_client_id: str
        plaid_secret: str
settings: Settings | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global Session
    global settings
    load_dotenv()
    settings = Settings()
    async_database_engine = create_async_engine(settings.async_sqlalchemy_database_uri)
    Session = sessionmaker(bind=async_database_engine, class_=AsyncSession, expire_on_commit=False)
    yield
    await async_database_engine.dispose()
    

app = FastAPI(lifespan=lifespan)

async def yield_db():
    async with Session() as session:
        yield session

def generate_random_id():
    ascii_letters = string.ascii_letters
    numbers = string.digits
    choices = ascii_letters + numbers
    uuid = ''.join([secrets.choice(choices) for _ in range(Constants.IDSizes.SMALL)])
    return uuid


'''
    HELPER UTILITY FUNCTIONS
        env_info
        refresh_database
'''
@app.get('/env_info')
def env_info():
    return {
        "sqlalchemy_database_uri": settings.sqlalchemy_database_uri,
        "test_plaid_url": settings.test_plaid_url,
        "test_plaid_client_id": settings.test_plaid_client_id,
        "plaid_secret": settings.plaid_secret
    }

@app.get('/refresh_database')
def refresh_database(dbsess: AsyncSession = Depends(yield_db)):
    temp_engine = create_engine(settings.sqlalchemy_database_uri)
    Base.metadata.drop_all(temp_engine)
    Base.metadata.create_all(temp_engine)
    temp_engine.dispose()
    return 'Database is refreshed!'

'''
    BATCH SCRIPTS: 'simulate' processing batch scripts


'''
class PlaidBalance(BaseModel):
    available: Optional[float | None] = None
    current: Optional[float | None] = None
    iso_currency_code: Optional[str | None] = None
    limit: Optional[float | None] = None
    unofficial_currency_code: Optional[str | None]

class PlaidAccount(BaseModel):
    account_id: Optional[str]
    balances: PlaidBalance
    mask: Optional[str | None] = None
    name: Optional[str | None] = None
    official_name: Optional[str | None] = None
    persistent_account_id: Optional[str | None] = None
    subtype: Optional[str | None] = None
    type: Optional[str | None] = None

@app.get('/batch/refresh_account_data')
async def refresh_account_data(dbsess: AsyncSession = Depends(yield_db)):
    smt = select(User.user_id, User.access_key)
    users = await dbsess.execute(smt)
    users = users.all()
    actions_result = []

    for user_id, access_key in users:
        # update the account data
        new_accounts = []
        current_accounts = set()
        cur_metadata = {
            'user_id': user_id,
            'account_updates': []
        }

        # keep track of current existing accounts in a set
        smt = select(Account.account_id).where(Account.user_id == user_id)
        current_account_ids = await dbsess.scalars(smt)
        current_account_ids = current_account_ids.all()

        for acc_id in current_account_ids:
            current_accounts.add(acc_id)

        # retrieve new account details
        async with httpx.AsyncClient() as client:
            client: httpx.AsyncClient
            resp = await client.post(
                f'{settings.test_plaid_url}/auth/get',
                headers={'Content-Type':'application/json'},
                json={
                    'client_id': settings.test_plaid_client_id,
                    'secret': settings.plaid_secret,
                    'access_token': access_key
                }
            )
            resp = resp.json()
            actual_response = resp
            
            new_accounts = resp['accounts']
            new_accounts = [PlaidAccount(**data) for data in resp['accounts']]

        if new_accounts:
            for cur_na in new_accounts:
                cur_na: PlaidAccount

                # need to create a new account
                if cur_na.account_id not in current_accounts:
                    dbsess.add(
                        Account(
                            account_id = cur_na.account_id,
                            balance_available = cur_na.balances.available,
                            balance_current = cur_na.balances.current,
                            iso_currency_code = cur_na.balances.iso_currency_code,
                            account_name = cur_na.name,
                            account_type = cur_na.type,
                            user_id = user_id
                        )
                    )

                    cur_metadata['account_updates'].append({
                        'account_id': cur_na.account_id,
                        'is_persistent': True if cur_na.persistent_account_id else False,
                        'action': 'created'
                    })
                else:
                    # already exists, so update
                    smt = update(Account).where(Account.account_id == cur_na.account_id).values({
                        'balance_available': cur_na.balances.available,
                        'balance_current': cur_na.balances.current
                    })

                    dbsess.execute(smt)

                    cur_metadata['account_updates'].append({
                        'account_id': cur_na.account_id,
                        'is_persistent': True if cur_na.persistent_account_id in current_accounts else False,
                        'action': 'updated'
                    })

                    current_accounts.remove(cur_na.account_id)

        actions_result.append(cur_metadata)
    
        for acc_id_remaining in current_accounts:
            smt = delete(Account).where(Account.account_id == acc_id_remaining)
            dbsess.execute(smt)

            actions_result.append({
                'account_id': acc_id_remaining,
                'is_persistent': None,
                'action': 'deleted'
            })
    
    try:
        await dbsess.commit()
    except Exception as e:
        await dbsess.rollback()
        print(e)
        raise HTTPException(status_code=500, detail='Database Operation Failed!') from e
    
    return {
        'endpoint': 'refresh_user_data',
        'actions_result': actions_result,
        'actual_response': actual_response
    }

class PlaidTransactionCounterparties(BaseModel):
    confidence_level: str | None
    entity_id: str | None
    logo_url: str | None
    name: str | None
    phone_number: str | None
    type: str | None
    website: str | None

class PlaidTransactionPersonalFinanceCategory(BaseModel):
    confidence_level: str | None
    detailed: str | None
    primary: str | None

class PlaidTransaction(BaseModel):
    account_id: str | None
    account_owner: str | None
    amount: float | None
    authorized_date: str | None
    authorized_datetime: str | None
    category: List[str] | None
    category_id: str | None
    counterparties: List[PlaidTransactionCounterparties] | None
    date: str
    datetime: str | None
    iso_currency_code: str | None
    logo_url: str | None
    merchant_entity_id: str | None
    merchant_name: str | None
    name: str | None
    payment_channel: str | None
    pending: bool | None
    personal_finance_category: PlaidTransactionPersonalFinanceCategory | None
    personal_finance_category_icon_url: str | None
    transaction_id: str | None
    website: str | None


@app.get('/batch/refresh_transaction_data')
async def refresh_transaction_data(dbsess: AsyncSession = Depends(yield_db)):

    smt = select(User.user_id, User.access_key)
    users = await dbsess.execute(smt)
    users = users.all()

    for user_id, access_key in users:

        if not access_key:
            continue
        
        cur_user = await dbsess.get(User, user_id)
        cur_transaction_cursor = cur_user.transactions_sync_cursor
        merchants_indb = await dbsess.scalars(select(Merchant.merchant_id))
        merchants_indb = set(merchants_indb.all())
        
        
        async with httpx.AsyncClient() as client:
            has_more = True

            added = []
            modified = []
            removed = []

            limit = 100
            while has_more:
                if limit == 0:
                    raise HTTPException(status_code=500, detail='Detected some sort of infinite loop while calling plaid api!')
                
                resp = await client.post(
                    f'{settings.test_plaid_url}/transactions/sync',
                    headers={'Content-Type': 'application/json'},
                    json={
                        'client_id': settings.test_plaid_client_id,
                        'secret': settings.plaid_secret,
                        'access_token': access_key,
                        'cursor': cur_transaction_cursor if cur_transaction_cursor else None,
                        'count': 500
                    }
                )

                resp = resp.json()

                added.extend(list(map(lambda r: PlaidTransaction(**r), resp['added'])))
                modified.extend(list(map(lambda r: PlaidTransaction(**r), resp['modified'])))
                removed.extend(list(map(lambda r: PlaidTransaction(**r), resp['removed'])))
                has_more = resp['has_more']
                cur_transaction_cursor = resp['next_cursor']
                limit -= 1
            
            cur_user.transactions_sync_cursor = cur_transaction_cursor

            for added_transaction in added:
                added_transaction: PlaidTransaction

                if not added_transaction.merchant_entity_id and ('not-available' not in merchants_indb):
                    dbsess.add(Merchant(merchant_id = 'not-available', merchant_name = "None", merchant_logo = "None"))
                    merchants_indb.add('not-available')
                    
                if not added_transaction.merchant_entity_id:
                    added_transaction.merchant_entity_id = 'not-available'
                
                if added_transaction.merchant_entity_id not in merchants_indb:
                    dbsess.add(Merchant(merchant_id = added_transaction.merchant_entity_id, \
                                              merchant_name = added_transaction.merchant_name, \
                                              merchant_logo = added_transaction.logo_url))
                    merchants_indb.add(added_transaction.merchant_entity_id)

                dbsess.add(
                    Transaction(
                        transaction_id = added_transaction.transaction_id,
                        amount = added_transaction.amount,
                        authorized_date = datetime.strptime(added_transaction.authorized_date, '%Y-%m-%d') if added_transaction.authorized_date else None,
                        personal_finance_category = added_transaction.personal_finance_category.primary,
                        user_id = user_id,
                        account_id = added_transaction.account_id,
                        merchant_id = added_transaction.merchant_entity_id
                    )
                )

            for modified_transaction in modified:
                modified_transaction: PlaidTransaction

                if not modified_transaction.merchant_entity_id and 'not-available' not in merchants_indb:
                    dbsess.add(Merchant(merchant_id = 'not-available', merchant_name = "None", merchant_logo = "None"))
                    merchants_indb.add('not-available')
                    
                if not modified_transaction.merchant_entity_id:
                    modified_transaction.merchant_entity_id = 'not-available'

                if modified_transaction.merchant_entity_id not in merchants_indb:
                    dbsess.add(Merchant(merchant_id = modified_transaction.merchant_entity_id, \
                                              merchant_name = modified_transaction.merchant_name, \
                                              merchant_logo = modified_transaction.logo_url))
                    merchants_indb.add(added_transaction.merchant_entity_id)

                smt = update(Transaction).where(Transaction.transaction_id == modified_transaction.transaction_id).values({
                    'amount': added_transaction.amount,
                    'authorized_date': datetime.strptime(added_transaction.authorized_date, '%Y-%m-%d') if added_transaction.authorized_date else None,
                    'personal_finance_category': added_transaction.personal_finance_category.primary,
                    'user_id': user_id,
                    'account_id': added_transaction.account_id,
                    'merchant_id': added_transaction.merchant_entity_id
                })

                await dbsess.execute(smt)

            for removed_transaction in removed:
                removed_transaction: PlaidTransaction

                smt = delete(Transaction).where(Transaction.transaction_id == removed_transaction.transaction_id)
                await dbsess.execute(smt)

    try:
        await dbsess.commit()
    except Exception as e:
        await dbsess.rollback()
        print(e)
        raise HTTPException(status_code=500, detail='Database Operation Failed!')
    
    return {
        'message': 'success'
    }


'''
    CLIENT SIDE API
        create_account
        link_account
        get_transactions

'''
class CreateAccountRequest(BaseModel):
    username: str
    password: str
    first_name: str
    last_name: str
    user_email: str
    user_profile_picture: Optional[str]

@app.post('/create_account')
async def create_account(request: CreateAccountRequest, dbsess: AsyncSession = Depends(yield_db)):

    uuid = generate_random_id()

    while (await dbsess.get(User, uuid)):
        uuid = generate_random_id()

    new_user = User(
        user_id=uuid,
        created_at=datetime.now(),
        last_login_at=datetime.now(),
        access_key=None,
        user_first_name=request.first_name,
        user_last_name=request.last_name,
        user_email=request.user_email,
        user_profile_picture=request.user_profile_picture
    )

    dbsess.add(new_user)

    try:
        await dbsess.commit()
    except Exception as e:
        await dbsess.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="Failed to create account") from e
    
    return {
        'message': 'success',
        'data': {
            'uuid': uuid
        }
    }


class GetPublicTokenRequest(BaseModel):
    user_id: str

async def plaid_get_public_token(uuid: str):
    async for dbsess in yield_db():
        async with dbsess.begin():
            public_token = None
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(f'{settings.test_plaid_url}/sandbox/public_token/create',
                                            headers={'Content-Type': 'application/json'},
                                            json={
                                                'client_id': settings.test_plaid_client_id,
                                                'secret': settings.plaid_secret,
                                                'institution_id': 'ins_20',
                                                'initial_products': ['transactions'],
                                                'options': {
                                                    'webhook': 'https://www.plaid.com/webhook'
                                                }
                                            })
                    resp = resp.json()
                    public_token = resp['public_token']
            except Exception as e:
                print(e)
                raise HTTPException(status_code=500, detail='Plaid Endpoint Request Failed') from e
            
            return public_token
    return None

@app.post('/get_public_token')
async def get_public_token(request: GetPublicTokenRequest):
    user_id = request.user_id
    public_token = await plaid_get_public_token(user_id)
    return {
        'public_token': public_token
    }

class ExchangePublicTokenRequest(BaseModel):
    user_id: str
    public_token: str

async def plaid_exchange_public_token(user_id, public_token):
    access_token = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f'{settings.test_plaid_url}/item/public_token/exchange',
                headers={'Content-Type': 'application/json'},
                json={
                    'client_id': settings.test_plaid_client_id,
                    'secret': settings.plaid_secret,
                    'public_token': public_token
                }
            )

            resp = resp.json()
            access_token = resp['access_token']
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Plaid Endpoint Failed!') from e
    

    try:
        async for dbsess in yield_db():
            async with dbsess.begin():
                cur_user = await dbsess.get(User, user_id)
                if not cur_user:
                    raise HTTPException(status_code=500, detail='User does not exist!')
                cur_user.access_key = access_token
                await dbsess.commit()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail='Database Update Failed!') from e


@app.post('/exchange_public_token')
async def exchange_public_token(request: ExchangePublicTokenRequest):
    await plaid_exchange_public_token(request.user_id, request.public_token)
    return {'message': 'success'}

class GetTransactionsRequest(BaseModel):
    user_id: str

@app.post('/get_transactions')
async def get_transactions(request: GetTransactionsRequest, dbsess: AsyncSession = Depends(yield_db)) -> List[PTransaction]:
    cur_user = await dbsess.get(User, request.user_id)
    if not cur_user:
        raise HTTPException(status_code=500, detail='Current User Does not Exist!')
    smt = select(Transaction).where(Transaction.user_id == request.user_id)
    transactions = await dbsess.scalars(smt)
    transactions = transactions.all()
    result = [PTransaction.model_validate(t) for t in transactions]
    return result