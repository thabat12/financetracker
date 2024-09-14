from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Boolean, LargeBinary, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    subscriptions = relationship('Subscription', backref='user', lazy='select', cascade='all, delete-orphan')
    auth_sessions = relationship('AuthSession', backref='user', lazy='select', cascade='all, delete-orphan')
    access_keys = relationship('AccessKey', backref='user', lazy='select', cascade='all, delete-orphan')
    investment_holdings = relationship('InvestmentHolding', backref='user', lazy='select', cascade='all, delete-orphan')

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
    subscriptions = relationship('Subscription', backref='merchant', lazy='select')

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
    
    # TODO
    institution_id = Column(String(Constants.IDSizes.MEDIUM), ForeignKey(f'{Institution.__tablename__}.institution_id'), nullable=True)

class InvestmentHolding(Base):
    __tablename__ = 'investment_holding'

    investment_holding_id = Column(String(Constants.IDSizes.LARGE), primary_key=True)
    name = Column(LargeBinary, nullable=True)
    ticker = Column(LargeBinary, nullable=True)
    cost_basis = Column(LargeBinary, nullable=True)
    institution_price = Column(Float, nullable=True)
    institution_price_as_of = Column(DateTime, nullable=True)
    institution_value = Column(Float, nullable=True)
    iso_currency_code = Column(String(Constants.IDSizes.SMALL), nullable=True)
    quantity = Column(LargeBinary, nullable=True)
    unofficial_currency_code = Column(String(Constants.IDSizes.SMALL), nullable=True)
    vested_quantity = Column(LargeBinary, nullable=True)
    vested_value = Column(LargeBinary, nullable=True)
    
    # relationships
    account_id = Column(String(Constants.IDSizes.MEDIUM), ForeignKey(f'{Account.__tablename__}.account_id'), nullable=True)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=True)

class Subscription(Base):
    __tablename__ = 'subscription'
    subscription_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(Constants.IDSizes.MEDIUM), nullable=False)
    price = Column(Float, nullable=False)
    renewal_date = Column(DateTime, nullable=False)

    # one (User) -> many (Subscription)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), \
                        nullable=False)
    
    # one (Merchant) -> many (Subscription)
    merchant_id = Column(String(Constants.IDSizes.SMALL), \
                            ForeignKey(f'{Merchant.__tablename__}.merchant_id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'renewal_date': self.renewal_date.isoformat()
        }

    def __repr__(self):
        return f'<Subscription {self.name}>'
    
class PORM(BaseModel):
    class Config:
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
    update_status: Optional[str] = None
    update_status_date: Optional[datetime] = None
    institution_id: str

    class Config:
        orm_mode = True

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

    class Config:
        orm_mode = True

class PSubscription(PORM):
    subscription_id: int