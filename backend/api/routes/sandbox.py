from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, select
from db.models import Subscription, Account, Transaction
from api.config import Config


database_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

sandbox_bp = Blueprint('sandbox', __name__)


def _to_dict(object, obj_type):
    res = {}
    for col in obj_type.__table__.columns:
        colname = col.name
        res[colname] = getattr(object, colname)

    return res


# Retrieve all subscriptions
@sandbox_bp.route('/subscriptions/get', methods=['POST'])
def get_subscriptions():

    subscriptions = []

    with Session(database_engine) as session:
        sql_smt = select(Subscription)
        subscriptions = session.scalars(sql_smt).all()
        print(subscriptions)

    return jsonify([_to_dict(subscription, Subscription) for subscription in subscriptions])

# Add a new subscription
@sandbox_bp.route('/subscriptions/add', methods=['POST'])
def add_subscription():
    data = request.get_json()
    new_subscription = Subscription(
        name=data['name'],
        price=data['price'],
        renewal_date=data['renewal_date'],
        user_id=data['user_id'],
        merchant_id=data.get('merchant_id')
    )

    with Session(database_engine) as session:
        session.add(new_subscription)
        session.commit()
    
    return jsonify(new_subscription.to_dict()), 201

# Delete a subscription
@sandbox_bp.route('/subscriptions/delete', methods=['POST'])
def delete_subscription():
    data = request.get_json()
    subscription = Subscription.query.get_or_404(data['id'])

    with Session(database_engine) as session:
        session.delete(subscription)
        session.commit()

    return '', 204

# Retrieve account details for a user
@sandbox_bp.route('/accounts/get', methods=['POST'])
def get_accounts():
    data = request.get_json()
    accounts = Account.query.filter_by(user_id=data['user_id']).all()
    return jsonify([account.to_dict() for account in accounts])

# Retrieve transactions for a specific account
@sandbox_bp.route('/transactions/get', methods=['POST'])
def get_transactions():
    data = request.get_json()
    transactions = Transaction.query.filter_by(account_id=data['account_id']).all()
    return jsonify([transaction.to_dict() for transaction in transactions])

# Add a new account
@sandbox_bp.route('/accounts/add', methods=['POST'])
def add_account():
    data = request.get_json()
    new_account = Account(
        name=data['name'],
        balance=data['balance'],
        user_id=data['user_id']
    )
    with Session(database_engine) as session:
        session.add(new_account)
        session.commit()

    return jsonify(new_account.to_dict()), 201

# Add a new transaction
@sandbox_bp.route('/transactions/add', methods=['POST'])
def add_transaction():
    data = request.get_json()
    new_transaction = Transaction(
        amount=data['amount'],
        date=data['date'],
        description=data.get('description', ''),
        account_id=data['account_id'],
        user_id=data['user_id'],
        merchant_id=data['merchant_id']
    )
    with Session(database_engine) as session:
        session.add(new_transaction)
        session.commit()

    return jsonify(new_transaction.to_dict()), 201
