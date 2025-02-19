from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Boolean, LargeBinary, Text, BigInteger
from sqlalchemy.orm import relationship, declarative_base

from pydantic import BaseModel, Field
from typing import Annotated, Optional, List
from datetime import datetime

class Constants:
    class IDSizes:
        SMALL = 20
        MEDIUM = 80
        LARGE = 255
        XLARGE = 1_000

Base = declarative_base()

class User(Base):
    __tablename__ = 'financetracker_user'
    # identification
    user_id = Column(String(Constants.IDSizes.SMALL), primary_key=True, nullable=False)
    user_type = Column(String(Constants.IDSizes.SMALL), nullable=True)
    is_verified = Column(Boolean, nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_login_at = Column(DateTime, nullable=False)
    user_first_name = Column(String(Constants.IDSizes.SMALL), nullable=False)
    user_last_name = Column(String(Constants.IDSizes.SMALL), nullable=True)
    user_email = Column(String(Constants.IDSizes.MEDIUM), nullable=False)
    user_profile_picture = Column(String(Constants.IDSizes.XLARGE), nullable=True)

    # encrypted data
    user_key = Column(LargeBinary(), nullable=True)

    # one to many
    accounts = relationship('Account', backref='user', lazy='select', cascade='all, delete-orphan')
    transactions = relationship('Transaction', backref='user', lazy='select', cascade='all, delete-orphan')
    auth_sessions = relationship('AuthSession', backref='user', lazy='select', cascade='all, delete-orphan')
    access_keys = relationship('AccessKey', backref='user', lazy='select', cascade='all, delete-orphan')
    investment_holdings = relationship('Holding', backref='user', lazy='select', cascade='all, delete-orphan')

class GoogleUser(Base):
    __tablename__ = 'google_user'
    google_user_id = Column(String(Constants.IDSizes.LARGE), primary_key=True, nullable=False)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)
    
    # one to one
    user = relationship('User', backref='google_user', uselist=False)

class Institution(Base):
    __tablename__ = 'institution'
    institution_id = Column(String(Constants.IDSizes.MEDIUM), primary_key=True) # todo: figure out the best length for this id
    name = Column(Text, nullable=True)
    supports_transactions = Column(Boolean, nullable=True)
    supports_investments = Column(Boolean, nullable=True)
    logo = Column(Text, nullable=True)
    url = Column(Text, nullable=True)

class AccessKey(Base):
    __tablename__ = 'access_key'
    # stored as <usr_id>:/:/:<ins_id>
    access_key_id = Column(String(Constants.IDSizes.LARGE), primary_key=True)
    access_key = Column(LargeBinary, nullable=False) # encrypted via the user key
    transactions_sync_cursor = Column(String(Constants.IDSizes.LARGE), nullable=True)
    last_transactions_account_sync = Column(DateTime, nullable=True)

    # one(User) -> many(AccessKey)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)

class AuthSession(Base):
    __tablename__ = 'auth_session'
    auth_session_token_id = Column(String(Constants.IDSizes.LARGE), primary_key=True, nullable=False)
    session_expiry_time = Column(DateTime, nullable=False)
    # one (User) -> many (AuthSession)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)

class Account(Base):
    __tablename__ = 'account'
    # note: use Plaid's persistent_account_id to populate this
    account_id = Column(String(Constants.IDSizes.MEDIUM), primary_key=True, nullable=False)

    balance_available = Column(LargeBinary, nullable=True)
    balance_current = Column(LargeBinary, nullable=True)
    iso_currency_code = Column(String(Constants.IDSizes.SMALL), nullable=True)
    account_name = Column(LargeBinary, nullable=True)
    account_type = Column(LargeBinary, nullable=True)
    update_status = Column(String(Constants.IDSizes.SMALL), nullable=True)
    update_status_date = Column(DateTime, nullable=True)

    # one to many
    transactions = relationship('Transaction', backref='account', lazy='select', cascade='all, delete-orphan')

    # one (User) -> many (Account)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)

    # i dont really know what this relationship is
    institution_id = Column(String(Constants.IDSizes.MEDIUM), ForeignKey(f'{Institution.__tablename__}.institution_id'), nullable=True)
    
    def __repr__(self) -> str:
        return f'{self.account_id}: {self.account_name}'
    
class Merchant(Base):
    __tablename__ = 'merchant'
    merchant_id = Column(String(Constants.IDSizes.MEDIUM), primary_key=True, \
                            nullable=False)
    merchant_name = Column(String(Constants.IDSizes.MEDIUM), nullable=False)
    merchant_logo = Column(String(Constants.IDSizes.LARGE), nullable=True)

    # one to many
    transactions = relationship('Transaction', backref='merchant', lazy='select')

class Transaction(Base):
    __tablename__ = 'transaction'
    transaction_id = Column(String(Constants.IDSizes.MEDIUM), primary_key=True, \
                               nullable=False)
    name = Column(LargeBinary, nullable=True)
    is_pending = Column(Boolean, nullable=True)
    amount = Column(LargeBinary, nullable=False)
    authorized_date = Column(DateTime, nullable=True)
    personal_finance_category = Column(LargeBinary, nullable=True)
    update_status = Column(String(Constants.IDSizes.SMALL), nullable=True)
    update_status_date = Column(DateTime, nullable=True)

    # one (User) -> many (Transaction)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), \
                        nullable=False)

    # one (Account) -> many (Transaction)
    account_id = Column(String(Constants.IDSizes.MEDIUM), \
                              ForeignKey(f'{Account.__tablename__}.account_id'), nullable=False)
    
    # one (Merchant) -> many (Transaction)
    merchant_id = Column(String(Constants.IDSizes.MEDIUM), \
                            ForeignKey(f'{Merchant.__tablename__}.merchant_id'), nullable=True)
    
    institution_id = Column(String(Constants.IDSizes.MEDIUM), ForeignKey(f'{Institution.__tablename__}.institution_id'), nullable=True)

class Security(Base):
    __tablename__ = "security"

    security_id = Column(String(Constants.IDSizes.LARGE), primary_key=True)
    institution_security_id = Column(String(Constants.IDSizes.MEDIUM), nullable=True)

    name = Column(String(Constants.IDSizes.LARGE), nullable=True)
    ticker_symbol = Column(String(Constants.IDSizes.MEDIUM), nullable=True)
    is_cash_equivalent = Column(Boolean, nullable=True)
    type = Column(String(Constants.IDSizes.MEDIUM), nullable=True)

    close_price = Column(Float, nullable=True)
    close_price_as_of = Column(DateTime, nullable=True)
    update_datetime = Column(DateTime, nullable=True)
    iso_currency_code = Column(String(10), nullable=True)
    unofficial_currency_code = Column(String(10), nullable=True)
    market_identifier_code = Column(String(10), nullable=True)
    sector = Column(String(Constants.IDSizes.MEDIUM), nullable=True)
    industry = Column(String(Constants.IDSizes.MEDIUM), nullable=True)

    # if you have options, this is a field on its own
    option_contract_type = Column(String(Constants.IDSizes.MEDIUM), nullable=True)
    option_expiration_date = Column(DateTime, nullable=True)
    option_strike_price = Column(Float, nullable=True)
    option_underlying_ticker = Column(String(Constants.IDSizes.MEDIUM), nullable=True)

    # if you have bonds
    percentage = Column(Float, nullable=True)
    maturity_date = Column(DateTime, nullable=True)
    issue_date = Column(DateTime, nullable=True)
    face_value = Column(Float, nullable=True)

class Holding(Base):
    __tablename__ = "holding"

    # I am getting holding data if it matches user-key anyways
    holding_id = Column(Integer, primary_key=True, autoincrement=True)
    institution_price = Column(LargeBinary, nullable=False)
    institution_price_as_of = Column(DateTime, nullable=True) # this is not super sensitive info
    institution_value = Column(LargeBinary, nullable=False)
    cost_basis = Column(LargeBinary, nullable=True)
    quantity = Column(LargeBinary, nullable=False)
    iso_currency_code = Column(String(Constants.IDSizes.MEDIUM), nullable=True) # not encrypted (bc why lol)
    unofficial_currency_code = Column(LargeBinary, nullable=True)
    vested_quantity = Column(LargeBinary, nullable=True)
    vested_value = Column(LargeBinary, nullable=True)

    # relationships
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), \
                     nullable=False)

    account_id = Column(String(Constants.IDSizes.MEDIUM), \
                              ForeignKey(f'{Account.__tablename__}.account_id'), nullable=False)
    
    security_id = Column(String(Constants.IDSizes.LARGE), \
                         ForeignKey(f'{Security.__tablename__}.security_id'), nullable=False)
    
    institution_id = Column(String(Constants.IDSizes.MEDIUM), \
                            ForeignKey(f'{Institution.__tablename__}.institution_id'), nullable=False)

class PORM(BaseModel):
    class ConfigDict:
        from_attributes = True

class PUser(PORM):
    user_id: str

class PAccount(PORM):
    account_id: str
    balance_available: Optional[float] = None
    balance_current: Optional[float] = None
    iso_currency_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    user_id: Optional[str] = None
    update_status: Optional[str] = None
    update_status_date: Optional[datetime] = None
    institution_id: str

    class ConfigDict:
        from_attributes = True

class PMerchant(PORM):
    merchant_id: str
    merchant_name: str
    merchant_logo: Optional[str] = None

class PTransaction(PORM):
    transaction_id: str
    name: Optional[str] = None
    amount: float
    authorized_date: Optional[datetime] = None
    personal_finance_category: Optional[str] = None
    update_status: Optional[str] = None
    update_status_date: Optional[datetime] = None

    # Relationships
    user_id: str
    account_id: str
    merchant_id: Optional[str] = None
    institution_id: str

    class ConfigDict:
        from_attributes = True

class PHolding(PORM):
    holding_id: str
    institution_price: float
    institution_price_as_of: Optional[datetime] = None
    institution_value: float
    cost_basis: Optional[float] = None
    quantity: float
    iso_currency_code: Optional[str] = None
    unofficial_currency_code: Optional[str] = None
    vested_quantity: Optional[float] = None
    vested_value: Optional[float] = None
    account_id: str
    security_id: str
    institution_id: str

    class ConfigDict:
        from_attributes = True

class PSecurity(PORM):
    security_id: str
    institution_security_id: Optional[str] = None

    name: str
    ticker_symbol: Optional[str] = None
    is_cash_equivalent: Optional[bool] = None
    type: Optional[str] = None

    close_price: Optional[float] = None
    close_price_as_of: Optional[float] = None
    update_datetime: Optional[datetime] = None
    iso_currency_code: Optional[str] = None
    unofficial_currency_code: Optional[str] = None
    market_identifier_code: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Option fields
    option_contract_type: Optional[str] = None
    option_expiration_date: Optional[str] = None
    option_strike_price: Optional[float] = None
    option_underlying_ticker: Optional[str] = None

    # Bond fields
    percentage: Optional[float] = None
    maturity_date: Optional[str] = None
    issue_date: Optional[str] = None
    face_value: Optional[float] = None

    # Relationships
    user_id: str
    account_id: str
    institution_id: str

    class ConfigDict:
        from_attributes = True

