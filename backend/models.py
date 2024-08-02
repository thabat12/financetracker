from flask_sqlalchemy import SQLAlchemy
from datetime import date

'''
    Constants:
        - length of strings defined to avoid hardcoding

'''
class Constants:
    class IDSizes:
        SMALL = 20
        MEDIUM = 80
        LARGE = 255
        XLARGE = 1_000

db: SQLAlchemy = SQLAlchemy()


class User(db.Model):
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
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), primary_key=True, \
                            nullable=False)
    merchant_name = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    merchant_logo = db.Column(db.String(Constants.IDSizes.LARGE), nullable=True)

    # one to many
    transactions = db.relationship('Transaction', backref='merchants', lazy=True)
    subscriptions = db.relationship('Subscription', backref='merchants', lazy=True)

class Transaction(db.Model):
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
    transation_id = db.Column(db.String(Constants.IDSizes.MEDIUM), \
                              db.ForeignKey('transaction.transaction_id'), nullable=False)
    
    # one (Merchant) -> many (Transaction)
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), \
                            db.ForeignKey('merchants.merchant_id'), nullable=False)
    
class Subscription(db.Model):
    subscription_id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(Constants.IDSizes.MEDIUM), nullable=False)
    price = db.Column(db.Float, nullable=False)
    renewal_date = db.Column(db.DateTime, nullable=False)

    # one (User) -> many (Subscription)
    user_id = db.Column(db.String(Constants.IDSizes.SMALL), db.ForeignKey('user.user_id'), \
                        nullable=False)
    
    # one (Merchant) -> many (Subscription)
    merchant_id = db.Column(db.String(Constants.IDSizes.SMALL), \
                            db.ForeignKey('merchants.merchant_id'), nullable=True)



    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'renewal_date': self.renewal_date.isoformat()
        }

    def __repr__(self):
        return f'<Subscription {self.name}>'
    
db.drop_all()
db.create_all()