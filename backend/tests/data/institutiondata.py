from datetime import datetime
from datetime import timedelta
from db.models import Institution, AccessKey

class InstitutionIDs:
    plaid_bank = 'ins_109508' # transactions & investments
    first_platypus_bank = 'ins_109510' # transactions
    tartan_bank = 'ins_109512' # transactions & investments
    pnc = 'ins_13' # transactions & investments

_institution_metadata = {
    'ins_109508' : {
        'name': 'First Platypus Bank',
        'supports_transactions': True,
        'supports_investments': True
    },
    'ins_109510': {  # First Platypus Bank
        'name': 'First Platypus Bank',
        'supports_transactions': True,
        'supports_investments': False  # Only transactions
    },
    'ins_109512': {  # Tartan Bank
        'name': 'Houndstooth Bank',
        'supports_transactions': True,
        'supports_investments': True  # Supports both transactions and investments
    },
    'ins_13': {  # PNC
        'name': 'PNC',
        'supports_transactions': True,
        'supports_investments': True  # Supports both transactions and investments
    }
}

def validate_institution(institution: Institution):
    assert institution.institution_id in _institution_metadata
    record = _institution_metadata[institution.institution_id]

    assert institution.supports_transactions == record['supports_transactions']
    assert institution.supports_investments == record['supports_investments']

def validate_access_key(
        access_key: AccessKey, institution: Institution, updated_time: datetime = None):
    cur_user: str = access_key.user_id
    
    # ensure the key is properly formatted
    # print(access_key.access_key_id)
    assert access_key.access_key_id == f'{cur_user}:/:/:{institution.institution_id}'
    assert access_key.user_id == cur_user

    # ensure a recent update (that is the most I can do for this validation)
    if updated_time:
        recent_time = datetime.now() - timedelta(minutes=2)
        assert access_key.last_transactions_account_sync >= recent_time
        assert access_key.transactions_sync_cursor is not None

    # otherwise, if there is a value for last_transactions_account_sync, then there
    #   must also be a value for the sync cursor
    if access_key.last_transactions_account_sync is not None:
        assert access_key.transactions_sync_cursor is not None

    