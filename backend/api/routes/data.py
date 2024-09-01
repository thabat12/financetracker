from enum import Enum
from pydantic import BaseModel
from logging import Logger
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from sqlalchemy import select, update, case, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import json

from api.config import Session, settings, logger
from api.routes.auth import verify_token
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data, encrypt_float, decrypt_float
from db.models import *


data_router = APIRouter()

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

class PlaidRefreshAccountsResponse(BaseModel):
    new: Optional[List[PlaidAccount]] = None
    updated: Optional[List[PlaidAccount]] = None
    deleted: Optional[List[PlaidAccount]] = None

'''
    returns a list of list of plaid account: new, updated, deleted

'''
async def plaid_refresh_accounts(user_id: str, user_access_key: str, user_key: bytes, institution_id: str = None) -> List[List[PlaidAccount]]:
    logger.info('/data/plaid_refresh_accounts')
    async with httpx.AsyncClient() as client:
        client: httpx.AsyncClient
        
        resp = await client.post(
            f'{settings.test_plaid_url}/auth/get',
            headers={'Content-Type':'application/json'},
            json={
                'client_id': settings.test_plaid_client_id,
                'secret': settings.plaid_secret,
                'access_token': user_access_key
            }
        )

        refreshed_account_data: List[PlaidAccount] = [PlaidAccount(**data) for data in resp.json()['accounts']]


    lock_key = hash(f'plaid_refresh_accounts:{user_id}') & 0x7fffffffffffffff

    async with Session() as session:
        async with session.begin():
            try:
                # this is a session-level lock
                await session.execute(text(f'SELECT pg_advisory_xact_lock({lock_key});'))

                smt = select(Account.account_id).where(Account.user_id == user_id)
                existing_account_ids = await session.scalars(smt)
                existing_account_ids = set(existing_account_ids.all())
                
                # keeping track of the account ids here
                refreshed_account_ids = set(account.account_id for account in refreshed_account_data)
                new_accounts = refreshed_account_ids - existing_account_ids
                updated_accounts = refreshed_account_ids & existing_account_ids
                deleted_accounts = existing_account_ids - refreshed_account_ids

                # update status related
                now = datetime.now()

                # filtering out new, updated, and deleted
                na, ua, da = [], [], []

                for account in refreshed_account_data:
                    if account.account_id in new_accounts:
                        na.append(account)
                    elif account.account_id in updated_accounts:
                        ua.append(account)
                    elif account.account_id in deleted_accounts:
                        da.append(account)
                    else:
                        raise Exception('there is an account neither added, updated, or deleted!!! what is happening?')

                new_accounts: List[PlaidAccount] = na
                updated_accounts: List[PlaidAccount] = ua
                deleted_accounts: List[PlaidAccount] = da

                if updated_accounts:
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
                                {account.account_id: now for account in updated_accounts},
                                value=Account.account_id
                            )
                        )
                        .where(Account.account_id.in_([account.account_id for account in updated_accounts]))
                    )

                if new_accounts:
                    session.add_all([
                        Account(
                            account_id = new_account.account_id,
                            balance_available = encrypt_float(new_account.balances.available, user_key),
                            balance_current = encrypt_float(new_account.balances.current, user_key),
                            iso_currency_code = new_account.balances.iso_currency_code,
                            account_name = encrypt_data(bytes(new_account.name, encoding='utf-8'), user_key),
                            account_type = encrypt_data(bytes(new_account.type, encoding='utf-8'), user_key),
                            user_id = user_id,
                            update_status = 'added',
                            update_status_date = now,
                            institution_id=institution_id
                        ) for new_account in new_accounts
                    ])

                if deleted_accounts:
                    smt = delete(Account).where(Account.account_id.in_(deleted_accounts))
                    await session.execute(smt)
                
                await session.commit()

                return PlaidRefreshAccountsResponse(new=new_accounts, updated=updated_accounts, deleted=deleted_accounts)
            
            except Exception as e:
                raise Exception('Database operation failed!', e)
                
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

'''
    returns a list of 3 elements of plaidtransaction objects: added, modified, removed

'''
async def plaid_refresh_transactions(user_id: str, user_access_key: str, user_key: bytes, institution_id: str, transactions_sync_cursor: str) -> List[PlaidTransaction]:
    logger.info('/data/plaid_refresh_transactions')
    transaction_hash = hash(f'plaid_refresh_transactions:{user_id}') & 0x7fffffffffffffff

    async with Session() as session:
        async with session.begin():
            await session.execute(text(f'SELECT pg_advisory_xact_lock({transaction_hash});'))
            # immediate employ a transaction lock on refresh_transactions
            user: User = await session.get(User, user_id)

            if not user:
                raise Exception('Whats going on: the user', user_id, 'is invalid!')

            cur_transactions_cursor: str | None = transactions_sync_cursor

            async with httpx.AsyncClient() as client:

                # need to be careful here because of a while loop so adding this limit stopper
                limit = 20
                has_more = True

                added, modified, removed = [], [], []

                while has_more:
                    if limit == 0:
                        raise HTTPException(status_code=500, detail=f'Detected more than {limit} calls to Plaid API on plaid_refresh_transactions!!! DANGER')
                    
                    print('the cur transactions cursor', cur_transactions_cursor)

                    resp = await client.post(
                        f'{settings.test_plaid_url}/transactions/sync',
                        headers={'Content-Type': 'application/json'},
                        json={
                            'client_id': settings.test_plaid_client_id,
                            'secret': settings.plaid_secret,
                            'access_token': user_access_key,
                            'cursor': cur_transactions_cursor if cur_transactions_cursor else None,
                            'count': 500
                        }
                    )
                    logger.info(f'/data/plaid_refresh_transactions: {user_id} plaid endpoint for /transactions/sync is called')
                    resp = resp.json()

                    print('THE DATA')
                    # print(json.dumps(resp, indent=4, sort_keys=True))

                    added.extend(list(map(lambda r: PlaidTransaction(**r), resp['added'])))
                    modified.extend(list(map(lambda r: PlaidTransaction(**r), resp['modified'])))
                    removed.extend(list(map(lambda r: PlaidTransaction(**r), resp['removed'])))

                    limit -= 1
                    has_more = resp['has_more']
                    cur_transactions_cursor = resp['next_cursor']

            # sets to monitor database changes
            current_merchants_indb = await session.scalars(select(Merchant.merchant_id))
            current_merchants_indb = set(current_merchants_indb.all())
            current_transactions_indb = await session.scalars(select(Transaction.transaction_id).where(Transaction.user_id == user_id))
            current_transactions_indb = set(current_transactions_indb.all())

            # current time 
            now = datetime.now()
            
            # set the transactions sync cursor
            new_transactions_cursor = cur_transactions_cursor

            logger.info(f'/data/plaid_refresh_transactions: {user_id} adding {len(added)} transactions to database')
            for added_transaction in added:
                added_transaction: PlaidTransaction

                # first populate the merchant data if applicable
                if added_transaction.merchant_entity_id and added_transaction.merchant_entity_id not in current_merchants_indb:
                    session.add(Merchant(merchant_id = added_transaction.merchant_entity_id, \
                                              merchant_name = added_transaction.merchant_name, \
                                              merchant_logo = added_transaction.logo_url))
                    current_merchants_indb.add(added_transaction.merchant_entity_id)

                session.add(
                    Transaction(
                        transaction_id = added_transaction.transaction_id,
                        name = encrypt_data(bytes(added_transaction.name, encoding='utf-8'), user_key),
                        is_pending = added_transaction.pending,
                        amount = encrypt_float(added_transaction.amount, user_key),
                        authorized_date = datetime.strptime(added_transaction.authorized_date, '%Y-%m-%d') if added_transaction.authorized_date else None,
                        personal_finance_category = encrypt_data(bytes(added_transaction.personal_finance_category.primary, encoding='utf-8'), user_key),
                        user_id = user_id,
                        account_id = added_transaction.account_id,
                        merchant_id = added_transaction.merchant_entity_id if added_transaction.merchant_entity_id is not None else None,
                        update_status = 'added',
                        update_status_date = now,
                        institution_id = institution_id
                    )
                )

            logger.info(f'/data/plaid_refresh_transactions: {user_id} modifying {len(modified)} transactions to database')
            for modified_transaction in modified:
                modified_transaction: PlaidTransaction

                if modified_transaction.transaction_id not in current_transactions_indb:
                    raise Exception('We are trying to modify a transaction id that doesnt exist onthe database!')

                if modified_transaction.merchant_entity_id and modified_transaction.merchant_entity_id not in current_merchants_indb:
                    session.add(Merchant(merchant_id = added_transaction.merchant_entity_id, \
                                              merchant_name = added_transaction.merchant_name, \
                                              merchant_logo = added_transaction.logo_url))
                    current_merchants_indb.add(modified_transaction.merchant_entity_id)
                    
                smt = update(Transaction).where(Transaction.transaction_id == modified_transaction.transaction_id).values({
                    'amount': encrypt_float(added_transaction.amount, user_key),
                    'authorized_date': datetime.strptime(added_transaction.authorized_date, '%Y-%m-%d') if added_transaction.authorized_date else None,
                    'personal_finance_category': encrypt_data(bytes(added_transaction.personal_finance_category.primary, encoding='utf-8'), user_key),
                    'user_id': user_id,
                    'account_id': added_transaction.account_id,
                    'merchant_id': added_transaction.merchant_entity_id,
                    'is_pending': added_transaction.pending,
                    'name': encrypt_data(bytes(added_transaction.name, encoding='utf-8'), user_key)
                })

                await session.execute(smt)

            logger.info(f'/data/plaid_refresh_transactions: {user_id} removing {len(removed)} transactions to database')
            for removed_transaction in removed:
                removed_transaction: PlaidTransaction

                if removed_transaction.transaction_id not in current_transactions_indb:
                    raise Exception('Trying to remove a transaction that does\'t even exist in the db!')
                smt = delete(Transaction).where(Transaction.transaction_id == removed_transaction.transaction_id)
                await session.execute(smt)

            await session.commit()

            logger.info(f'/data/plaid_refresh_transactions: {user_id} transaction modifications set')
            return PlaidRefreshTransactionsResponse(added=added, modified=modified, removed=removed, new_transactions_cursor=new_transactions_cursor)

async def plaid_refresh_user_account_data(user_id: str, user_key: bytes):
    logger.info('/data/plaid_refresh_user_account_data')

    # get all the accounts associated with the current user
    async with Session() as session:
        async with session.begin():
            logger.info(f'/data/plaid_refresh_user_account_data: selecting all access keys that are associated with the user')
            smt = select(AccessKey).where(AccessKey.user_id == user_id)

            access_keys = await session.execute(smt)
            access_keys = access_keys.scalars().all()

            if not access_keys:
                logger.error(f'/data/plaid_refresh_user_account_data: {user_id} this endpoint is called without any access keys??')
                raise HTTPException(detail='User has no access keys but the plaid_refresh_user_account_data endpoint is\n' + \
                                        'somehow called!', status_code=500)

            logger.info(f'/data/plaid_refresh_user_account_data: {user_id} definitely has some access keys so let us process them!')

            print(access_keys, 'is all the access keys')
            all_user_institutions = [i.access_key_id.split(':/:/:')[-1].strip() for i in access_keys]
            smt = select(Institution).where(Institution.institution_id.in_(all_user_institutions))

            logger.info(f'/data/plaid_refresh_user_account_data: {user_id} getting all the institution data metadata for user')
            all_institution_data = await session.execute(smt)
            all_institution_data = all_institution_data.scalars().all()
            all_institution_data = { i.institution_id: i for i in all_institution_data }

    try:
        logger.info(f'/data/plaid_refresh_user_account_data: {user_id} setting up iteration through all access keys and associated institutions')
        # refresh the user data for every access key that has institution data support
        updated_access_keys = []
        updated_transaction_sync_cursors = []
        for cur_institution, access_key_record in zip(all_user_institutions, access_keys):
            access_key_record: AccessKey

            # do i need an update here? avoid updates if the data is already updated
            if access_key_record.last_transactions_account_sync != None and access_key_record.last_transactions_account_sync.day == datetime.now().day:
                continue
        
            user_access_key = decrypt_data(access_key_record.access_key, user_key).decode('utf-8')
            cur_institution_data: Institution = all_institution_data[cur_institution]

            if cur_institution_data.supports_auth:
                logger.info(f'/data/plaid_refresh_user_account_data: {user_id} institution {cur_institution} supports auth!')
                await plaid_refresh_accounts(user_id=user_id, user_access_key=user_access_key, user_key=user_key, institution_id=cur_institution)
            if cur_institution_data.supports_transactions:
                logger.info(f'/data/plaid_refresh_user_account_data: {user_id} institution {cur_institution} supports transactions!')
                resp: PlaidRefreshTransactionsResponse = await plaid_refresh_transactions(user_id=user_id, user_access_key=user_access_key, 
                                                                                          user_key=user_key, institution_id=cur_institution, 
                                                                                          transactions_sync_cursor=access_key_record.transactions_sync_cursor)

            updated_access_keys.append(access_key_record.access_key_id)
            updated_transaction_sync_cursors.append(resp.new_transactions_cursor)

        logger.info(f'/data/plaid_refresh_user_account_data: {user_id} refreshed account and transaction data')

        # avoid updating anything related to the sync cursors if there is nothing to update
        if not updated_access_keys:
            return

        # upon successful 
        async with Session() as session:
            async with session.begin():
                logger.info(f'/data/plaid_refresh_user_account_data: {user_id} updating the access key items associated with user')

                logger.info(f'/data/plaid_refresh_user_account_data: {user_id} the updated access keys are {updated_access_keys} and the sync cursors are {updated_transaction_sync_cursors}')

                smt = update(AccessKey).values(
                    last_transactions_account_sync=case(
                        {akid: datetime.now() for akid in updated_access_keys},
                        value=AccessKey.access_key_id
                    ),
                    transactions_sync_cursor=case(
                        {akid: cursor for akid, cursor in zip(updated_access_keys, updated_transaction_sync_cursors)},
                        value=AccessKey.access_key_id
                    )
                ).where(AccessKey.user_id == user_id)
                await session.execute(smt)
    except Exception as e:
        raise e

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

async def db_get_transactions(user_id: str, data_type: DBGetTransactionsEnum) -> DBGetTransactionsResponse:
    logger.info('/data/db_get_transactions')
    async with Session() as session:
        async with session.begin():
            cur_user: User = await session.get(User, user_id)
            user_key = decrypt_data(cur_user.user_key, db_key_bytes)

    # necessary account + transaction data refresh
    await plaid_refresh_user_account_data(user_id=user_id, user_key=user_key)
    
    # get all the transactions
    async with Session() as session:
        async with session.begin():
            logger.info(f'/data/db_get_transactions: {user_id} filling in all transaction/ account data as response object')
            cur_user: User = await session.get(User, user_id)

            if data_type == DBGetTransactionsEnum.TRANSACTIONS:
                # all_<> comes from the database
                all_transactions = await session.scalars(select(Transaction).where(User.user_id == cur_user.user_id))
                all_transactions = all_transactions.all()

                transactions: List[PTransaction] = []
                merchant_ids: List[str] = []

                for transaction in all_transactions:
                    # handle data decryption manually here
                    transaction: Transaction
                    transactions.append(PTransaction(
                        transaction_id=transaction.transaction_id,
                        name=decrypt_data(transaction.name, user_key).decode('utf-8'),
                        amount=decrypt_float(transaction.amount, user_key),
                        authorized_date=transaction.authorized_date,
                        personal_finance_category=decrypt_data(transaction.personal_finance_category, user_key).decode('utf-8'),
                        update_status=transaction.update_status,
                        update_status_date=transaction.update_status_date,
                        user_id=transaction.user_id,
                        account_id=transaction.account_id,
                        merchant_id=transaction.merchant_id,
                        institution_id=transaction.institution_id
                    ))
                    merchant_ids.append(transaction.merchant_id)

                all_merchants = await session.scalars(select(Merchant).where(Merchant.merchant_id.in_(merchant_ids)))
                all_merchants: List[Merchant] = all_merchants.all()

                merchants: List[PMerchant] = []

                for merchant in all_merchants:
                    merchant: Merchant
                    merchants.append(PMerchant.model_validate(merchant))
                
                transactions_resp = DBGetTransactionsResponseTransactions(transactions=transactions, merchants=merchants)
                logger.info(f'/data/db_get_transactions: {user_id} all transaction information filled in!')
                return DBGetTransactionsResponse(transactions=transactions_resp)
            
            elif data_type == DBGetTransactionsEnum.ACCOUNTS:
                all_accounts = await session.scalars(select(Account).where(Account.user_id == cur_user.user_id))
                all_accounts = all_accounts.all()

                accounts: List[PAccount] = []

                for account in all_accounts:
                    account: Account
                    # manually decrypting the account data
                    accounts.append(
                        PAccount(
                            account_id=account.account_id,
                            balance_available=decrypt_float(account.balance_available, user_key),
                            balance_current=decrypt_float(account.balance_current, user_key),
                            iso_currency_code=account.iso_currency_code,
                            account_name=decrypt_data(account.account_name, user_key).decode('utf-8'),
                            account_type=decrypt_data(account.account_type, user_key).decode('utf-8'),
                            update_status=account.update_status,
                            update_status_date=account.update_status_date,
                            institution_id=account.institution_id
                        )
                    )
                logger.info(f'/data/db_get_transactions: {user_id} all accounts information filled in!')

                accounts_resp: DBGetTransactionsResponseAccounts = DBGetTransactionsResponseAccounts(accounts=accounts)

                return DBGetTransactionsResponse(accounts=accounts_resp)

class GetTransactionsResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'

class GetTransactionsResponse(BaseModel):
    message: GetTransactionsResponseEnum = None
    transactions: Optional[List[PTransaction]] = None
    merchants: Optional[List[PMerchant]] = None

@data_router.post('/get_transactions')
async def get_transactions(authorization: str = Header(...)) -> GetTransactionsResponse:
    logger.info('/data/get_transactions')
    token = authorization.strip().split(' ')[-1].strip()

    res: bool
    cur_user: str
    (res, cur_user) = await verify_token(token)

    if not cur_user:
        logger.error(f'/data/get_transactions: provided authorization token is invalid!')
        return GetTransactionsResponse(message=GetTransactionsResponseEnum.INVALID_AUTH)

    if res:
        transactions: DBGetTransactionsResponse = await db_get_transactions(user_id=cur_user, data_type=DBGetTransactionsEnum.TRANSACTIONS)
        transactions: DBGetTransactionsResponseTransactions = transactions.transactions
        # re-parse everything to the gettransactionsresponse object
        transactions = GetTransactionsResponse(message=GetTransactionsResponseEnum.SUCCESS,transactions=transactions.transactions, merchants=transactions.merchants)

    logger.info(f'/data/get_transactions: the data returned!')
    return transactions

class GetAccountsResponseEnum(Enum):
    SUCCESS = 'success'
    INVALID_AUTH = 'invalid_auth'

class GetAccountsResponse(BaseModel):
    message: GetAccountsResponseEnum
    accounts: List[PAccount]

@data_router.post('/get_accounts')
async def get_accounts(authorization: str = Header(...)) -> GetAccountsResponse:
    token = authorization.strip().split(' ')[-1].strip()

    res: bool
    cur_user: str
    (res, cur_user) = await verify_token(token)

    if not cur_user:
        raise HTTPException(status_code=500, detail='User session is invalid!')
    
    if res:
        accounts: DBGetTransactionsResponse = await db_get_transactions(user_id=cur_user, data_type=DBGetTransactionsEnum.ACCOUNTS)

    return GetAccountsResponse(message=GetAccountsResponseEnum.SUCCESS, accounts=accounts.accounts.accounts)