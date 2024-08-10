from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey, Boolean
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
    access_key = Column(String(Constants.IDSizes.MEDIUM), nullable=True)
    user_first_name = Column(String(Constants.IDSizes.SMALL), nullable=False)
    user_last_name = Column(String(Constants.IDSizes.SMALL), nullable=True)
    user_email = Column(String(Constants.IDSizes.MEDIUM), nullable=False)
    user_profile_picture = Column(String(Constants.IDSizes.XLARGE), nullable=True)
    transactions_sync_cursor = Column(String(Constants.IDSizes.LARGE), nullable=True)

    # one to many
    accounts = relationship('Account', backref='user', lazy='select', cascade='all, delete-orphan')
    transactions = relationship('Transaction', backref='user', lazy='select', cascade='all, delete-orphan')
    subscriptions = relationship('Subscription', backref='user', lazy='select', cascade='all, delete-orphan')
    auth_sessions = relationship('AuthSession', backref='user', lazy='select', cascade='all, delete-orphan')

class GoogleUser(Base):
    __tablename__ = 'google_user'
    google_user_id = Column(String(Constants.IDSizes.LARGE), primary_key=True, nullable=False)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)
    
    # one to one
    user = relationship('User', backref='google_user', uselist=False)

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

    balance_available = Column(Float, nullable=True)
    balance_current = Column(Float, nullable=True)
    iso_currency_code = Column(String(Constants.IDSizes.SMALL), nullable=True)
    account_name = Column(String(Constants.IDSizes.LARGE), nullable=True)
    account_type = Column(String(Constants.IDSizes.SMALL), nullable=True)

    # one to many
    transactions = relationship('Transaction', backref='account', lazy='select', cascade='all, delete-orphan')

    # one (User) -> many (Account)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), nullable=False)
    
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
    amount = Column(Float, nullable=False)
    authorized_date = Column(DateTime, nullable=True)
    personal_finance_category = Column(String(Constants.IDSizes.MEDIUM), nullable=True)

    # one (User) -> many (Transaction)
    user_id = Column(String(Constants.IDSizes.SMALL), ForeignKey(f'{User.__tablename__}.user_id'), \
                        nullable=False)

    # one (Account) -> many (Transaction)
    account_id = Column(String(Constants.IDSizes.MEDIUM), \
                              ForeignKey(f'{Account.__tablename__}.account_id'), nullable=False)
    
    # one (Merchant) -> many (Transaction)
    merchant_id = Column(String(Constants.IDSizes.MEDIUM), \
                            ForeignKey(f'{Merchant.__tablename__}.merchant_id'), nullable=False)
    
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

class PMerchant(PORM):
    merchant_id: str

class PTransaction(PORM):
    transaction_id: str

class PSubscription(PORM):
    subscription_id: int