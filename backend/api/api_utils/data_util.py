from enum import Enum
import asyncio
from pydantic import BaseModel
from datetime import timedelta
from logging import Logger
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from sqlalchemy import select, update, case, delete, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from api.config import settings, logger
from api.api_utils.auth_util import verify_token
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data, encrypt_float, decrypt_float
from db.models import *

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
    cur_user: User = await session.scalar(select(User.user_key).where(User.user_id == cur_user))
    user_key: bytes = decrypt_data(cur_user.user_key, db_key_bytes)

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

# READ ONLY: only retrieve transactions based on the current user being selected
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

    logger.info('util method called: db_find_update_access_keys')

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
    
    # ensure reordering of all institutions
    all_institutions: List[Institution] = reorder_institutions_helper(all_institutions=all_institutions)

    return (access_keys, all_institutions)

# helper function for db_update_transactions
async def plaid_get_refreshed_transactions(
        user_access_key: str,
        transactions_sync_cursor: str,
        client: httpx.AsyncClient
    ) -> tuple[List[PlaidTransaction], ...]:

    added, modified, removed = [], [], []

    for _ in range(20):
        resp = await client.post(
            f'{settings.test_plaid_url}/transactions/sync',
            headers={'Content-Type': 'application/json'},
            json={
                'client_id': settings.test_plaid_client_id,
                'secret': settings.plaid_secret,
                'access_token': user_access_key,
                'cursor': transactions_sync_cursor,
                'count': 500
            }
        )

        resp = resp.json()

        added.extend(list(map(lambda r: PlaidTransaction(**r), resp['added'])))
        modified.extend(list(map(lambda r: PlaidTransaction(**r), resp['modified'])))
        removed.extend(list(map(lambda r: PlaidTransaction(**r), resp['removed'])))

        transactions_sync_cursor = resp['next_cursor']

        if not resp['has_more']:
            break

    return added, modified, removed

# helper function for plaid_refresh_transactions -- also handles encryption
def map_plaid_transaction_to_transaction(
        plaid_transaction: PlaidTransaction, 
        cur_user: str, 
        user_key: bytes, 
        institution_id: str,
        update_status: str
    ) -> Transaction:

    return Transaction(
        transaction_id = plaid_transaction.transaction_id,
        name = encrypt_data(bytes(plaid_transaction.name, encoding='utf-8'), user_key),
        is_pending = plaid_transaction.pending,
        amount = encrypt_float(plaid_transaction.amount, user_key),
        authorized_date = datetime.strptime(plaid_transaction.authorized_date, '%Y-%m-%d') \
            if plaid_transaction.authorized_date else None,
        personal_finance_category = encrypt_data(
            bytes(plaid_transaction.personal_finance_category.primary, encoding='utf-8'), user_key
        ),
        user_id = cur_user,
        account_id = plaid_transaction.account_id,
        merchant_id = plaid_transaction.merchant_entity_id \
            if plaid_transaction.merchant_entity_id is not None else None,
        update_status = update_status,
        update_status_date = datetime.now(),
        institution_id = institution_id
    )

# helper function for plaid_refresh_transactions -- handles modified transaction state changes
async def db_update_plaid_transaction(
       plaid_transaction: PlaidTransaction,
       user_key: bytes,
       cur_user: str,
       session: AsyncSession
    ) -> None:

    smt = update(Transaction).where(Transaction.transaction_id == plaid_transaction.transaction_id).values({
        'amount': encrypt_float(plaid_transaction.amount, user_key),
        'authorized_date': datetime.strptime(plaid_transaction.authorized_date, '%Y-%m-%d') \
            if plaid_transaction.authorized_date else None,
        'personal_finance_category': encrypt_data(
            bytes(plaid_transaction.personal_finance_category.primary, encoding='utf-8'), user_key
        ),
        'user_id': cur_user,
        'account_id': plaid_transaction.account_id,
        'merchant_id': plaid_transaction.merchant_entity_id,
        'is_pending': plaid_transaction.pending,
        'name': encrypt_data(bytes(plaid_transaction.name, encoding='utf-8'), user_key)
    })
    await session.execute(smt)

# helper function for plaid_refresh_transactions -- handles simply deleting transactions on the database
async def db_remove_plaid_transaction(
        plaid_transaction: PlaidTransaction,
        session: AsyncSession
    ) -> None:
    
    smt = delete(Transaction).where(Transaction.transaction_id == plaid_transaction.transaction_id)
    await session.execute(smt)

# helper method: gives the plain access key string
def decrypt_access_key(access_key: bytes, user_key: bytes) -> str:
    return decrypt_data(access_key, user_key).decode('utf-8')

async def db_update_transactions(
        cur_user: str,
        user_key: bytes,
        all_institutions: List[Institution],
        access_keys: List[AccessKey],
        session: AsyncSession
    ) -> None:
    
    for cur_institution, cur_access_key in zip(all_institutions, access_keys):
        decrypted_access_key: str = decrypt_access_key(cur_access_key.access_key, user_key=user_key)

        if not cur_institution.supports_transactions:
            return
        
        added, modified, removed = await plaid_get_refreshed_transactions(user_access_key=decrypted_access_key, \
                                            transactions_sync_cursor=cur_access_key.transactions_sync_cursor)
        
        for ind, a in enumerate(added):
            added[ind] = map_plaid_transaction_to_transaction(plaid_transaction=a, cur_user=cur_user, \
                user_key=user_key, institution_id=cur_institution.institution_id, update_status='added')
            
        session.add_all(added)

        for m in modified:
            # indirectly calling session.execute
            await db_update_plaid_transaction(plaid_transaction=m, user_key=user_key, \
                cur_user=cur_user, session=session)
            
        for r in removed:
            # indirectly calling session.execute
            await db_remove_plaid_transaction(plaid_transaction=r, session=session)

        await session.commit()

def map_plaid_account_to_account(
        plaid_account: PlaidAccount,
        user_key: bytes,
        cur_user: str
    ):

    return Account(
        account_id = plaid_account.account_id,
        balance_available = encrypt_float(plaid_account.balances.available, user_key),
        balance_current = encrypt_float(plaid_account.balances.current, user_key),
        iso_currency_code = plaid_account.balances.iso_currency_code,
        account_name = encrypt_data(bytes(plaid_account.name, encoding='utf-8'), user_key),
        account_type = encrypt_data(bytes(plaid_account.type, encoding='utf-8'), user_key),
        user_id = cur_user,
        update_status = 'added',
        update_status_date = datetime.now(),
        institution_id=plaid_account.institution_id
    )

async def db_update_plaid_accounts(
        user_key: bytes,
        session: AsyncSession,
        updated_accounts: List[PlaidAccount],
    ) -> None:

    await session.execute(
        update(Account)
        .values(
            balance_available=case(
                {account.account_id: encrypt_float(account.balances.available, user_key) for account in updated_accounts},
                value=Account.account_id
            ),
            balance_current=case(
                {account.account_id: encrypt_float(account.balances.current, user_key) for account in updated_accounts},
                value=Account.account_id
            ),
            update_status=case(
                {account.account_id: 'updated' for account in updated_accounts},
                value=Account.account_id
            ),
            update_status_date=case(
                {account.account_id: datetime.now() for account in updated_accounts},
                value=Account.account_id
            )
        )
        .where(Account.account_id.in_([account.account_id for account in updated_accounts]))
    )

async def db_delete_plaid_accounts(
       deleted_accounts: set[str],
       session: AsyncSession 
    ) -> None:
    smt = delete(Account).where(Account.account_id.in_(deleted_accounts))
    await session.execute(smt)

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
                f'{settings.test_plaid_url}/accounts/get',
                headers={'Content-Type':'application/json'},
                json={
                    'client_id': settings.test_plaid_client_id,
                    'secret': settings.plaid_secret,
                    'access_token': decrypted_user_access_key
                }
            )

        all_data = resp.json()
        all_data['institution_id'] = cur_institution

        all_accounts.extend([PlaidAccount(**data) for data in all_data['accounts']])

    return all_accounts


async def db_update_accounts(
        cur_user: str, 
        user_key: bytes,
        refreshed_account_data: List[PlaidAccount],
        all_institutions: List[Institution],
        session: AsyncSession
    ) -> None:

    smt = select(Account.account_id).where(and_(Account.user_id == cur_user, \
                                                Account.institution_id.in_(all_institutions)))
    existing_account_ids = await session.scalars(smt)
    existing_account_ids = set(existing_account_ids.all())
    
    refreshed_account_ids = set(account.account_id for account in refreshed_account_data)
    new_accounts = refreshed_account_ids - existing_account_ids
    updated_accounts = refreshed_account_ids & existing_account_ids
    deleted_accounts = existing_account_ids - refreshed_account_ids

    na, ua, da = [], [], []
    for cur_refreshed_account in refreshed_account_data:
        if cur_refreshed_account.account_id in new_accounts:
            na.append(cur_refreshed_account)
        elif cur_refreshed_account.account_id in updated_accounts:
            ua.append(cur_refreshed_account)
        else:
            da.append(cur_refreshed_account)

    new_accounts, updated_accounts, deleted_accounts = na, ua, da
 

    for i, na in enumerate(new_accounts):
        new_accounts[i] = map_plaid_account_to_account(plaid_account=na, user_key=user_key)

    session.add_all(new_accounts)

    if updated_accounts:
        db_update_plaid_accounts(user_key=user_key, session=session, updated_accounts=updated_accounts)

    if deleted_accounts:
        db_delete_plaid_accounts(deleted_accounts=deleted_accounts, session=session)

    await session.commit()

async def db_get_accounts(
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
    
    return GetTransactionsResponse(message=GetAccountsResponseEnum.SUCCESS, transactions=all_transactions)