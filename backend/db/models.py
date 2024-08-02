from flask_sqlalchemy import SQLAlchemy
from datetime import date

from api.app import app

class Constants:
    class IDSizes:
        SMALL = 20
        MEDIUM = 80
        LARGE = 255
        XLARGE = 1_000

db: SQLAlchemy = SQLAlchemy(app=app)

class User(db.Model):
    __tablename__ = 'user'
    # identification
    user_id = db.Column(db.String(Constants.IDSizes.SMALL), primary_key=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    access_key = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=True)
    user_first_name = db.Column(db.String(Constants.IDSizes.SMALL), nullable=False)
    user_last_name = db.Column(db.String(Constants.IDSizes.SMALL), nullable=False)
    user_email = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    user_profile_picture = db.Column(db.String(Constants.IDSizes.XLARGE), nullable=True)

    # one to many
    accounts = db.relationship('Account', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    
class Account(db.Model):
    __tablename__ = 'account'
    # note: use Plaid's persistent_account_id to populate this
    account_id = db.Column(db.String(Constants.IDSizes.MEDIUM), primary_key=True, nullable=False)

    balance_available = db.Column(db.Float, nullable=True)
    balance_current = db.Column(db.Float, nullable=True)
    iso_currency_code = db.Column(db.String(Constants.IDSizes.SMALL), nullable=True)
    account_name = db.Column(db.String(Constants.IDSizes.LARGE), nullable=True)
    account_type = db.Column(db.String(Constants.IDSizes.SMALL), nullable=True)

    # one to many
    transactions = db.relationship('Transaction', backref='account', lazy=True)

    # one (User) -> many (Account)
    user_id = db.Column(db.String(Constants.IDSizes.SMALL), db.ForeignKey('user.user_id'), \
                        nullable=False)
    
class Merchant(db.Model):
    __tablename__ = 'merchant'
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), primary_key=True, \
                            nullable=False)
    merchant_name = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    merchant_logo = db.Column(db.String(Constants.IDSizes.LARGE), nullable=True)

    # one to many
    transactions = db.relationship('Transaction', backref='merchant', lazy=True)
    subscriptions = db.relationship('Subscription', backref='merchant', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    transaction_id = db.Column(db.String(Constants.IDSizes.MEDIUM), primary_key=True, \
                               nullable=False)
    amount = db.Column(db.Float, nullable=False)
    authorized_date = db.Column(db.DateTime, nullable=False)
    merchant_name = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    merchant_logo = db.Column(db.String(Constants.IDSizes.LARGE), nullable=True)
    personal_finance_category = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)

    # one (User) -> many (Transaction)
    user_id = db.Column(db.String(Constants.IDSizes.SMALL), db.ForeignKey('user.user_id'), \
                        nullable=False)
    
    # one (Account) -> many (Transaction)
    account_id = db.Column(db.String(Constants.IDSizes.MEDIUM), \
                              db.ForeignKey('account.account_id'), nullable=False)
    
    # one (Merchant) -> many (Transaction)
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), \
                            db.ForeignKey('merchant.merchant_id'), nullable=False)
    
class Subscription(db.Model):
    __tablename__ = 'subscription'
    subscription_id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    price = db.Column(db.Float, nullable=False)
    renewal_date = db.Column(db.DateTime, nullable=False)

    # one (User) -> many (Subscription)
    user_id = db.Column(db.String(Constants.IDSizes.SMALL), db.ForeignKey('user.user_id'), \
                        nullable=False)
    
    # one (Merchant) -> many (Subscription)
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), \
                            db.ForeignKey('merchant.merchant_id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'renewal_date': self.renewal_date.isoformat()
        }

    def __repr__(self):
        return f'<Subscription {self.name}>'