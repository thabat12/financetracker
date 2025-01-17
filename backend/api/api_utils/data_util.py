from enum import Enum
import asyncio
from pydantic import BaseModel
from datetime import timedelta
from sqlalchemy import select, insert, update, case, delete, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from settings import settings
from api.config import get_global_session, logger
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data, encrypt_float, decrypt_float
from db.models import *

import logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)  # Set level to WARNING or ERROR
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Suppress query logs

'''
    Constants: 

'''
REFRESH_TIMEDELTA = timedelta(days=1)

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
    institution_id: Optional[str | None] = None

class PlaidRefreshAccountsResponse(BaseModel):
    new: Optional[List[PlaidAccount]] = None
    updated: Optional[List[PlaidAccount]] = None
    deleted: Optional[List[PlaidAccount]] = None

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

class PlaidHolding(BaseModel):
    account_id: str
    cost_basis: Optional[float] = None
    institution_price: float
    institution_price_as_of: Optional[datetime] = None
    institution_price_datetime: Optional[datetime] = None
    institution_value: float
    iso_currency_code: Optional[str] = None
    quantity: float
    security_id: str
    unofficial_currency_code: Optional[str] = None
    vested_quantity: Optional[float] = None
    vested_value: Optional[float] = None
    institution_id: Optional[str] = None

class PlaidOptionContract(BaseModel):
    contract_type: str
    expiration_date: datetime
    strike_price: float
    underlying_security_ticker: str

class PlaidYieldRate(BaseModel):
    percentage: float
    type: Optional[str] = None

class PlaidFixedIncome(BaseModel):
    yield_rate: Optional[PlaidYieldRate]
    maturity_date: Optional[datetime] = None
    issue_date: Optional[str] = None
    face_value: Optional[float] = None

class PlaidSecurity(BaseModel):
    close_price: Optional[float] = None
    close_price_as_of: Optional[datetime] = None
    cusip: Optional[str] = None
    fixed_income: Optional[PlaidFixedIncome] = None
    industry: Optional[str] = None
    institution_id: Optional[str] = None
    institution_security_id: Optional[str] = None
    is_cash_equivalent: Optional[bool] = None
    isin: Optional[str] = None
    iso_currency_code: Optional[str] = None
    market_identifier_code: Optional[str] = None
    name: Optional[str] = None
    option_contract: Optional[PlaidOptionContract] = None
    proxy_security_id: Optional[str] = None
    sector: Optional[str] = None
    security_id: str
    sedol: Optional[str] = None
    ticker_symbol: Optional[str] = None
    type: Optional[str] = None
    unofficial_currency_code: Optional[str] = None
    update_datetime: Optional[datetime] = None       

class PlaidRefreshTransactionsResponse(BaseModel):
    added: Optional[List[PlaidTransaction]] = None
    modified: Optional[List[PlaidTransaction]] = None
    removed: Optional[List[PlaidTransaction]] = None
    new_transactions_cursor: str = None

class DBGetTransactionsEnum(Enum):
    TRANSACTIONS = 1
    ACCOUNTS = 2

class DBGetTransactionsResponseTransactions(BaseModel):
    transactions: List[PTransaction]
    merchants: List[PMerchant]

class DBGetTransactionsResponseAccounts(BaseModel):
    accounts: List[PAccount]

class DBGetTransactionsResponse(BaseModel):
    transactions: Optional[DBGetTransactionsResponseTransactions] = None
    accounts: Optional[DBGetTransactionsResponseAccounts] = None

class GetTransactionsResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'

class GetTransactionsResponse(BaseModel):
    message: GetTransactionsResponseEnum = None
    transactions: Optional[List[PTransaction]] = None

class GetAccountsResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'

class GetAccountsResponse(BaseModel):
    message: GetAccountsResponseEnum
    accounts: List[PAccount]


'''
    Util functions:


'''
# use session object and the global key to identify the current user_key in bytes
async def decrypt_user_key(cur_user: str, session: AsyncSession) -> bytes:
    cur_user_encrypted_key: bytes = await session.scalar(select(User.user_key).where(User.user_id == cur_user))

    # TODO: fix issues related to this
    if not cur_user_encrypted_key:
        print("ther is no user to be found... let's take a look at everything on this database for user")
        all_users = await session.execute(select(User))
        all_users = all_users.all()
        print("all users are...")
        for user in all_users:
            print(f"user_id: {user.user_id} | user_key: {user.user_key}")
        print("... and those are all users")
        raise Exception("the current user encrypted key is not found!")

    user_key: bytes = decrypt_data(cur_user_encrypted_key, db_key_bytes)

    return user_key

# helper method in db_get_transactions to decrypt necessary data
def decrypt_transaction_data(transaction: Transaction, user_key: bytes) -> PTransaction:
    return PTransaction(
        transaction_id=transaction.transaction_id,
        name=decrypt_data(transaction.name, user_key).decode('utf-8'),
        amount=decrypt_float(transaction.amount, user_key),
        authorized_date=transaction.authorized_date,
        personal_finance_category=decrypt_data(
                                    transaction.personal_finance_category, 
                                    user_key).decode('utf-8'),
        update_status=transaction.update_status,
        update_status_date=transaction.update_status_date,
        user_id=transaction.user_id,
        account_id=transaction.account_id,
        merchant_id=transaction.merchant_id,
        institution_id=transaction.institution_id
    )

# helper method for encrypting holdings
def encrypt_if_not_null(dataobj: str | float, user_key: bytes) -> bytes | None:
    if dataobj is not None:
        if type(dataobj) == str:
            return encrypt_data(bytes(dataobj, encoding="utf-8"), user_key)
        elif type(dataobj) == float:
            return encrypt_float(dataobj, user_key)
        else:
            raise Exception(f"have not implemented encrypt_if_not_null on type: {type(dataobj)}")
    else:
        return None

# convert plaid response to security model to be compatible with database
def plaid_security_data_to_security_model(plaid_security: PlaidSecurity):
    return Security(
        security_id=plaid_security.security_id,
        institution_security_id=plaid_security.institution_security_id,
        name=plaid_security.name,
        ticker_symbol=plaid_security.ticker_symbol,
        is_cash_equivalent=plaid_security.is_cash_equivalent,  # Not encrypted
        type=plaid_security.type,
        close_price=plaid_security.close_price,
        close_price_as_of=plaid_security.close_price_as_of,
        update_datetime=plaid_security.update_datetime,
        iso_currency_code=plaid_security.iso_currency_code,
        unofficial_currency_code=plaid_security.unofficial_currency_code,
        market_identifier_code=plaid_security.market_identifier_code,
        sector=plaid_security.sector,
        industry=plaid_security.industry,
        option_contract_type=plaid_security.option_contract.contract_type \
            if plaid_security.option_contract else None,
        option_expiration_date=plaid_security.option_contract.expiration_date \
            if plaid_security.option_contract else None,
        option_strike_price=plaid_security.option_contract.strike_price \
            if plaid_security.option_contract else None,
        option_underlying_ticker=plaid_security.option_contract.underlying_security_ticker \
            if plaid_security.option_contract else None,
        percentage=plaid_security.fixed_income.yield_rate.percentage \
            if plaid_security.fixed_income else None,
        issue_date=plaid_security.fixed_income.issue_date \
            if plaid_security.fixed_income else None,
        face_value=plaid_security.fixed_income.face_value \
            if plaid_security.fixed_income else None
    )

def encrypt_holdings_model(plaid_holding: PlaidHolding, cur_user: str, user_key: bytes):
    return Holding(
        # data
        institution_price=encrypt_float(plaid_holding.institution_price, user_key),
        institution_price_as_of=plaid_holding.institution_price_as_of,
        institution_value=encrypt_float(plaid_holding.institution_value, user_key),
        cost_basis=encrypt_if_not_null(plaid_holding.cost_basis, user_key),
        quantity=encrypt_float(plaid_holding.quantity, user_key),
        iso_currency_code=plaid_holding.iso_currency_code,
        unofficial_currency_code=plaid_holding.unofficial_currency_code,
        vested_quantity=encrypt_if_not_null(plaid_holding.vested_quantity, user_key),
        vested_value=encrypt_if_not_null(plaid_holding.vested_value, user_key),
        # relations
        user_id=cur_user,
        account_id=plaid_holding.account_id,
        security_id=plaid_holding.security_id,
        institution_id=plaid_holding.institution_id
    )

# READ ONLY: only retrieve transactions based on the current user selected
async def db_get_transactions(
        cur_user: str, 
        user_key: bytes, 
        session: AsyncSession
    ) -> GetTransactionsResponse:
    
    logger.info('util method caled: db_get_transactions')
    all_transactions: List = await session.scalars(select(Transaction) \
                                                    .where(Transaction.user_id == cur_user))
    
    all_transactions = all_transactions.all()
    
    all_transactions = map(lambda t: decrypt_transaction_data(transaction=t, user_key=user_key), \
                           all_transactions)
    all_transactions = list(all_transactions)
    
    return GetTransactionsResponse(message=GetTransactionsResponseEnum.SUCCESS, transactions=all_transactions)

def reorder_institutions_helper(institution_ids: List[str], all_institutions: List[Institution]):
    institution_mapper = { ins_id: i for i, ins_id in enumerate(institution_ids) }
    return sorted(all_institutions, key = lambda i: institution_mapper[i.institution_id])

# READ ONLY
async def db_get_all_institution_data(institution_ids: List[str], session: AsyncSession):
    smt = select(Institution).where(Institution.institution_id.in_(institution_ids))

    all_institutions = await session.execute(smt)
    all_institutions: List[Institution] = all_institutions.scalars().all()

    return all_institutions

# db_update_transactions helper method: give only the access keys that need to be updated
async def db_get_access_key_updates(
        cur_user: str,
        session: AsyncSession
    ) -> tuple[List[AccessKey], List[Institution]]:

    logger.info('util method called: db_get_access_key_updates')

    # find any access key that has its updated time greater than yesterday-ago or has never refreshed
    smt = select(AccessKey) \
            .where(and_(AccessKey.user_id == cur_user, \
            or_(AccessKey.last_transactions_account_sync == None, \
                AccessKey.last_transactions_account_sync < datetime.today())))

    access_keys = await session.execute(smt)
    access_keys: List[AccessKey] = access_keys.scalars().all()

    institution_ids = [i.access_key_id.split(':/:/:')[-1].strip() for i in access_keys]
    all_institutions: List[Institution] = await db_get_all_institution_data(institution_ids=institution_ids, \
                                                                            session=session)
    
    # ensure reordering of all institutions to correspond with access keys
    all_institutions: List[Institution] = reorder_institutions_helper(institution_ids=institution_ids, \
                                                                      all_institutions=all_institutions)

    return (access_keys, all_institutions)

# helper function for db_update_transactions
async def plaid_get_refreshed_transactions(
        access_key: AccessKey,
        user_key: bytes,
        client: httpx.AsyncClient
    ) -> tuple[List[PlaidTransaction], ...]:

    decrypted_access_key: str = decrypt_access_key(access_key=access_key.access_key, user_key=user_key)
    transactions_sync_cursor = access_key.transactions_sync_cursor
    added, modified, removed = [], [], []

    for _ in range(20):
        resp = await client.post(
            url=f'{settings.plaid_url}/transactions/sync',
            headers={'Content-Type': 'application/json'},
            json={
                'client_id': settings.plaid_client_id,
                'secret': settings.plaid_secret,
                'access_token': decrypted_access_key,
                'cursor': transactions_sync_cursor,
                'count': 500
            }
        )

        resp = resp.json()
        
        # wait at least 10 seconds before pulling is ready
        if resp['transactions_update_status'] != 'HISTORICAL_UPDATE_COMPLETE':
            logger.info('status is not ready yet, allowing for some wait time')
            await asyncio.sleep(10)
            continue # try again

        added.extend(list(map(lambda r: PlaidTransaction(**r), resp['added'])))
        modified.extend(list(map(lambda r: PlaidTransaction(**r), resp['modified'])))
        removed.extend(list(map(lambda r: PlaidTransaction(**r), resp['removed'])))

        transactions_sync_cursor = resp['next_cursor']

        if not resp['has_more']:
            break

    # set the access key's transaction sync cursor and on next commit the result will stick
    access_key.transactions_sync_cursor = transactions_sync_cursor

    return added, modified, removed

# helper method: gives the plain access key string
def decrypt_access_key(access_key: bytes, user_key: bytes) -> str:
    return decrypt_data(access_key, user_key).decode('utf-8')

async def db_batch_update_merchants_data(
    added: List[PlaidTransaction],
    modified: List[PlaidTransaction],
    removed: List[PlaidTransaction],
    session: AsyncSession  
    ) -> None:
    '''
        using a lazy-pattern of updating merchant data based on all the transactions
        that the current transactions/sync endpoint has returned. all merchant data
        is stored on the transaction objects.

        streamlining 
    '''
    logger.info('db_batch_update_merchants_data')
    merchant_data = {}
    for transaction in [*added, *modified, *removed]:
        if transaction.merchant_entity_id is not None and \
            transaction.merchant_entity_id not in merchant_data:

            merchant_data[transaction.merchant_entity_id] = {
                'merchant_name': transaction.merchant_name,
                'merchant_logo': transaction.logo_url
            }

    # map the parameters & values to the sql injection statement properly
    params = {}
    for merchant_id, data in merchant_data.items():
        params[f'{merchant_id}_merchant_name'] = data['merchant_name']
        params[f'{merchant_id}_merchant_logo'] = data['merchant_logo']

    values = []
    for merchant_id in merchant_data.keys():
        values.append(f'(\'{merchant_id}\', :{merchant_id}_merchant_name, :{merchant_id}_merchant_logo)')
    values_str = ', '.join(values)

    # custom SQL injection
    smt = text(
        f'INSERT INTO {Merchant.__tablename__} (merchant_id, merchant_name, merchant_logo)' + \
        f' VALUES {values_str} ON CONFLICT (merchant_id) DO UPDATE SET' + \
        ' merchant_name = EXCLUDED.merchant_name, merchant_logo = EXCLUDED.merchant_logo;')

    # logger.info(smt)
    await session.execute(smt, params)
    await session.commit()

async def db_update_transactions(
        cur_user: str,
        user_key: bytes,
        all_institutions: List[Institution],
        access_keys: List[AccessKey],
        session: AsyncSession,
        client: httpx.AsyncClient
    ) -> None:
    
    for cur_institution, cur_access_key in zip(all_institutions, access_keys):
        if not cur_institution.supports_transactions:
            continue
        
        # note thhat this function also modifies the transactions_sync_cursor in the database
        added, modified, removed = await plaid_get_refreshed_transactions(
            access_key=cur_access_key, user_key=user_key, client=client)
        
        # there is no update work to do
        if not added and not modified and not removed:
            continue
        
        # ensure that all merchant data is set
        await db_batch_update_merchants_data(added=added, modified=modified, \
                                             removed=removed, session=session)
        

        # goal: simplify adding + modifying into one single execute statement

        updated_transaction_values = []
        updated_transaction_params = {}
        for updated_transaction in [*added, *modified]:
            cur_transaction: PlaidTransaction = updated_transaction
            cur_transaction_id = cur_transaction.transaction_id

            updated_transaction_values.append(
                f'(\'{cur_transaction_id}\', :{cur_transaction_id}_name, :{cur_transaction_id}_is_pending, ' + \
                    f':{cur_transaction_id}_amount, :{cur_transaction_id}_authorized_date, ' + \
                    f':{cur_transaction_id}_personal_finance_category, \'created\', ' + \
                    f':{cur_transaction_id}_update_status_date, :{cur_transaction_id}_user_id, ' + \
                    f':{cur_transaction_id}_account_id, :{cur_transaction_id}_merchant_id, :{cur_transaction_id}_institution_id)'
            )

            updated_transaction_params[f"{cur_transaction_id}_name"] = \
                encrypt_data(bytes(updated_transaction.name, encoding='utf-8'), user_key)
            updated_transaction_params[f"{cur_transaction_id}_is_pending"] = updated_transaction.pending
            updated_transaction_params[f"{cur_transaction_id}_amount"] = encrypt_float(updated_transaction.amount, user_key)
            updated_transaction_params[f"{cur_transaction_id}_authorized_date"] = \
                datetime.strptime(updated_transaction.authorized_date, '%Y-%m-%d') if updated_transaction.authorized_date else None
            updated_transaction_params[f"{cur_transaction_id}_personal_finance_category"] = \
                encrypt_data(bytes(updated_transaction.personal_finance_category.primary, encoding='utf-8'), user_key)
            updated_transaction_params[f"{cur_transaction_id}_update_status_date"] = datetime.now()
            updated_transaction_params[f"{cur_transaction_id}_user_id"] = cur_user
            updated_transaction_params[f"{cur_transaction_id}_account_id"] = updated_transaction.account_id
            updated_transaction_params[f"{cur_transaction_id}_merchant_id"] = \
                updated_transaction.merchant_entity_id if updated_transaction.merchant_entity_id is not None else None
            updated_transaction_params[f"{cur_transaction_id}_institution_id"] = cur_institution.institution_id

        insert_smt = text(f"""
            INSERT INTO {Transaction.__tablename__}
                VALUES {', '.join(updated_transaction_values)}
            ON CONFLICT (transaction_id)
                DO UPDATE SET
                    name=EXCLUDED.name,
                    is_pending=EXCLUDED.is_pending,
                    amount=EXCLUDED.amount,
                    authorized_date=EXCLUDED.authorized_date,
                    personal_finance_category=EXCLUDED.personal_finance_category,
                    update_status='updated',
                    update_status_date=EXCLUDED.update_status_date,
                    user_id=EXCLUDED.user_id,
                    account_id=EXCLUDED.account_id,
                    merchant_id=EXCLUDED.merchant_id,
                    institution_id=EXCLUDED.institution_id;
        """)

        removed_transaction_ids = [f"'{r.transaction_id}'" for r in removed]

        delete_smt = text(f"""
            DELETE FROM {Transaction.__tablename__}
                WHERE transaction_id IN ({", ".join(removed_transaction_ids)}) AND user_id = {f"'{cur_user}'"};
        """)

        if added or modified:
            await session.execute(insert_smt, updated_transaction_params)
        if removed:
            await session.execute(delete_smt)

        await session.commit()

# gives every single plaid account that exists under all the user keys updated
async def plaid_get_refreshed_accounts(
        user_key: bytes,
        user_access_keys: List[AccessKey],
        all_institutions: List[Institution],
        client: httpx.AsyncClient
    ) -> List[PlaidAccount]:

    all_accounts = []

    for cur_institution, cur_user_access_key in zip(all_institutions, user_access_keys):
        decrypted_user_access_key: str = decrypt_access_key(access_key=cur_user_access_key.access_key, \
                                                            user_key=user_key)
        resp = await client.post(
                f'{settings.plaid_url}/accounts/get',
                headers={'Content-Type':'application/json'},
                json={
                    'client_id': settings.plaid_client_id,
                    'secret': settings.plaid_secret,
                    'access_token': decrypted_user_access_key
                }
            )

        all_data = resp.json()
        all_data['institution_id'] = cur_institution

        all_accounts.extend([PlaidAccount(**data, institution_id=cur_institution.institution_id) for data in all_data['accounts']])

    return all_accounts


def execute_account_insert_update_statement(
        user_key: bytes,
        cur_user: str,
        refreshed_account_data: List[PlaidAccount]
    ) -> tuple[text, dict]:

    values = []
    params = {}
    dt_now = datetime.now() # prevent unecessary recomputation of this

    for account_data in refreshed_account_data:
        aid = account_data.account_id
        values.append(
            f'(\'{aid}\', :{aid}_balance_available, :{aid}_balance_current, :{aid}_iso_currency_code, ' + \
                f':{aid}_account_name, :{aid}_account_type, :{aid}_update_status, :{aid}_update_status_date, ' + \
                f':{aid}_user_id, :{aid}_institution_id)'
        )

        params[f'{aid}_balance_available'] = encrypt_float(account_data.balances.available, user_key)
        params[f'{aid}_balance_current'] = encrypt_float(account_data.balances.current, user_key)
        params[f'{aid}_iso_currency_code'] = account_data.balances.iso_currency_code
        params[f'{aid}_account_name'] = encrypt_data(bytes(account_data.name, encoding='utf-8'), user_key)
        params[f'{aid}_account_type'] = encrypt_data(bytes(account_data.type, encoding='utf-8'), user_key)
        params[f'{aid}_update_status'] = 'added'
        params[f'{aid}_update_status_date'] = dt_now
        params[f'{aid}_user_id'] = cur_user
        params[f'{aid}_institution_id'] = account_data.institution_id
    
    values_str = ', '.join(values)


    # handle insertions and updates in one go
    smt = text(f'''
        INSERT INTO {Account.__tablename__}
            VALUES {values_str}
        ON CONFLICT (account_id)
            DO UPDATE SET
                balance_available=EXCLUDED.balance_available,
                balance_current = EXCLUDED.balance_current,
                update_status = 'updated',
                update_status_date = EXCLUDED.update_status_date;
    ''')

    return smt, params

def execute_account_delete_statement(
        cur_user: str,
        refreshed_account_data: List[PlaidAccount]
    ) -> tuple[text, dict]:

    if not refreshed_account_data:
        return

    refreshed_values_ids = list(map(lambda pa: f"\'{pa.account_id}\'", refreshed_account_data))

    smt = text(f'''
        DELETE FROM {Account.__tablename__}
            WHERE account_id NOT IN ({",".join(refreshed_values_ids)}) AND user_id = :cur_user;
    ''')

    params = {'cur_user': cur_user}
    
    return smt, params

async def db_update_accounts(
        cur_user: str, 
        user_key: bytes,
        access_keys: List[AccessKey],
        all_institutions: List[Institution],
        session: AsyncSession,
        client: httpx.AsyncClient
    ) -> None:
    '''
        Streamline SQL query operation to two statements.
    '''
    logger.info("db_update_accounts called")
    refreshed_account_data: List[PlaidAccount] = None
    refreshed_account_data = await plaid_get_refreshed_accounts(user_key=user_key, user_access_keys=access_keys, \
                                         all_institutions=all_institutions, client=client)
    
    insert_update_smt, insert_params = execute_account_insert_update_statement(
        cur_user=cur_user, refreshed_account_data=refreshed_account_data, user_key=user_key)
    delete_smt, delete_params =  execute_account_delete_statement(
        cur_user=cur_user, refreshed_account_data=refreshed_account_data)

    await session.execute(insert_update_smt, insert_params)
    await session.execute(delete_smt, delete_params)
    await session.commit()

def decrypt_account_data(account: Account, user_key: bytes) -> PAccount:
    return PAccount(
        account_id=account.account_id,
        balance_available = decrypt_float(account.balance_available, user_key),
        balance_current = decrypt_float(account.balance_available, user_key),
        iso_currency_code = account.iso_currency_code,
        account_name = decrypt_data(account.account_name, user_key).decode(encoding='utf-8'),
        account_type = decrypt_data(account.account_type, user_key).decode(encoding='utf-8'),
        user_id = account.user_id,
        update_status = 'added',
        update_status_date = datetime.now(),
        institution_id=account.institution_id
    )

async def db_get_accounts(
        cur_user: str, 
        user_key: bytes, 
        session: AsyncSession
    ) -> GetTransactionsResponse:
    
    logger.info('util method caled: db_get_accounts')
    all_accounts: List = await session.scalars(select(Account) \
                                                    .where(Account.user_id == cur_user))
    
    all_accounts = all_accounts.all()
    
    all_accounts = map(lambda a: decrypt_account_data(transaction=a, user_key=user_key), \
                           all_accounts)
    
    return GetAccountsResponse(message=GetAccountsResponseEnum.SUCCESS, accounts=all_accounts)

async def plaid_get_refreshed_investments(
        user_key: bytes,
        user_access_keys: List[AccessKey],
        all_institutions: List[Institution],
        client: httpx.AsyncClient
    ) -> tuple[List[PlaidHolding], List[PlaidSecurity]]:
    all_holdings = []
    all_securities = []
    seen_securities = set()

    for cur_institution, cur_user_access_key in zip(all_institutions, user_access_keys):

        # no investments means cannot get this data :(
        if not cur_institution.supports_investments:
            continue
        
        print('getting investments data from institution:', cur_institution.institution_id)
        decrypted_user_access_key: str = decrypt_access_key(access_key=cur_user_access_key.access_key, \
                                                            user_key=user_key)
        
        resp = await client.post(
                f'{settings.plaid_url}/investments/holdings/get',
                headers={'Content-Type': 'application/json'},
                json={
                    'client_id': settings.plaid_client_id,
                    'secret': settings.plaid_secret,
                    'access_token': decrypted_user_access_key
                }
            )
        
        resp = resp.json()
        holdings_data = resp['holdings']
        security_data = resp['securities']

        holdings_data = [PlaidHolding.model_validate({**obj, "institution_id": cur_institution.institution_id}) for obj in holdings_data]
        security_data = [PlaidSecurity.model_validate(obj) for obj in security_data]

        all_holdings.extend(holdings_data)
        # duplicate security ids may exist...
        for security in security_data:
            if security.security_id not in seen_securities:
                all_securities.append(security)

            seen_securities.add(security.security_id)

    return all_holdings, all_securities

def execute_security_insert_update_statement(refreshed_securities: List[Security]) -> tuple[text, dict]:
    # get the securities values & params
    securities_values = []
    securities_params = {}

    for ind, refreshed_security in enumerate(refreshed_securities):
        refreshed_security: Security
        txt = f"('{refreshed_security.security_id}', :{ind}_institution_security_id, :{ind}_name, :{ind}_ticker_symbol, " + \
            f":{ind}_is_cash_equivalent, :{ind}_type, :{ind}_close_price, :{ind}_close_price_as_of, :{ind}_update_datetime, :{ind}_iso_currency_code, " + \
            f":{ind}_unofficial_currency_code, :{ind}_market_identifier_code, :{ind}_sector, :{ind}_industry, :{ind}_option_contract_type, " + \
            f":{ind}_option_expiration_date, :{ind}_option_strike_price, :{ind}_option_underlying_ticker, :{ind}_percentage, " + \
            f":{ind}_maturity_date, :{ind}_issue_date, :{ind}_face_value)"
        
        securities_values.append(txt)

        securities_params.update({
            f"{ind}_institution_security_id": refreshed_security.institution_security_id,
            f"{ind}_name": refreshed_security.name,
            f"{ind}_ticker_symbol": refreshed_security.ticker_symbol,
            f"{ind}_is_cash_equivalent": refreshed_security.is_cash_equivalent,
            f"{ind}_type": refreshed_security.type,
            f"{ind}_close_price": refreshed_security.close_price,
            f"{ind}_close_price_as_of": refreshed_security.close_price_as_of,
            f"{ind}_update_datetime": refreshed_security.update_datetime,
            f"{ind}_iso_currency_code": refreshed_security.iso_currency_code,
            f"{ind}_unofficial_currency_code": refreshed_security.unofficial_currency_code,
            f"{ind}_market_identifier_code": refreshed_security.market_identifier_code,
            f"{ind}_sector": refreshed_security.sector,
            f"{ind}_industry": refreshed_security.industry,
            f"{ind}_option_contract_type": refreshed_security.option_contract_type,
            f"{ind}_option_expiration_date": refreshed_security.option_expiration_date,
            f"{ind}_option_strike_price": refreshed_security.option_strike_price,
            f"{ind}_option_underlying_ticker": refreshed_security.option_underlying_ticker,
            f"{ind}_percentage": refreshed_security.percentage,
            f"{ind}_maturity_date": refreshed_security.maturity_date,
            f"{ind}_issue_date": refreshed_security.issue_date,
            f"{ind}_face_value": refreshed_security.face_value
        })

    securities_smt = text(f"""
        INSERT INTO {Security.__tablename__}
            VALUES {', '.join(securities_values)}
        ON CONFLICT (security_id)
        DO UPDATE SET
            close_price=EXCLUDED.close_price,
            close_price_as_of=EXCLUDED.close_price_as_of,
            update_datetime=EXCLUDED.update_datetime,
            option_expiration_date=EXCLUDED.option_expiration_date;
    """)

    return securities_smt, securities_params
        

async def db_update_investments(
        cur_user: str,
        user_key: bytes,
        access_keys: list[AccessKey],
        all_institutions: list[Institution],
        session: AsyncSession,
        client: httpx.AsyncClient
    ) -> None:
    print("db_update_investments called")
    # holdings are the user's actual data, whereas securities are metadata over a specific type of asset
    refreshed_holdings, refreshed_securities = await plaid_get_refreshed_investments( \
        user_key=user_key, user_access_keys=access_keys, all_institutions=all_institutions, client=client)

    print("mapping all investment holdings to ORM...")
    # translate all holdings into models
    refreshed_holdings: List[Holding] = [
        encrypt_holdings_model(
            plaid_holding=plaid_holding, 
            user_key=user_key, 
            cur_user=cur_user
        ) for plaid_holding in refreshed_holdings
    ]

    print("mapping all securities to ORM...")
    refreshed_securities: List[Security] = [
        plaid_security_data_to_security_model(plaid_security=plaid_security) \
            for plaid_security in refreshed_securities
    ]

    print("generating the insert update statements for securities...")
    securities_smt, securities_params = execute_security_insert_update_statement(refreshed_securities)

    if refreshed_securities:
        print("executing securities statements")
        await session.execute(securities_smt, securities_params)

    if refreshed_holdings:
        print("sending all data with...")
        # holdings are a bit more simple
        holdings_delete_smt = delete(Holding).where(and_(Holding.user_id == cur_user))
        await session.execute(holdings_delete_smt)
        session.add_all(refreshed_holdings)
    
    print("commit time baby")
    await session.commit()

'''
    Asynchronous DB updates: on every login and link account, there will be an asynchronous
        database update triggered. this will simply go over all the current access keys that need
        to be updated by the user, updates them, and then sets the corresponding data on access keys
        to their respective values.
'''
async def db_update_transaction_account_sync(access_keys: List[AccessKey], session: AsyncSession) -> None:
    updated_time = datetime.now()

    for access_key in access_keys:
        access_key.last_transactions_account_sync = updated_time

    await session.commit()

"""
    db_update_all_data_asynchronously:
        this method goes through all the user's data through Plaid API refresh calls and updates the
        database with the proper user-associated data. 

"""
async def db_update_all_data(cur_user: str, session: AsyncSession, client: httpx.AsyncClient):
    user_key: bytes = await decrypt_user_key(cur_user=cur_user, session=session)

    access_keys, institutions = await db_get_access_key_updates(cur_user=cur_user, session=session)
    access_keys: list[AccessKey]
    institutions: list[Institution]

    # update transactions & accounts with all the necessary data required
    await db_update_accounts(cur_user=cur_user, user_key=user_key, access_keys=access_keys, \
                            all_institutions=institutions, session=session, client=client)
    await db_update_transactions(cur_user=cur_user, user_key=user_key, all_institutions=institutions, \
                                    access_keys=access_keys, session=session, client=client)
    await db_update_investments(cur_user=cur_user, user_key=user_key, access_keys=access_keys, \
                                all_institutions=institutions, session=session, client=client)
    await db_update_transaction_account_sync(access_keys=access_keys, session=session)


async def db_update_all_data_asynchronously(cur_user: str, session: AsyncSession = None, \
                                            client: httpx.AsyncClient = None):

    if not session and not client:
        logger.info(f'db_update_all_data_asynchronously for: {cur_user}')
        global_session = get_global_session()

        async with global_session() as session:
            async with httpx.AsyncClient(timeout=30) as client:
                await db_update_all_data(cur_user=cur_user, session=session, client=client)
    else:
        logger.info(f'db_update_all_data for: {cur_user} -- synchronous wait')
        await db_update_all_data(cur_user=cur_user, session=session, client=client)

            