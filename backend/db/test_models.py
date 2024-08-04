import os
import requests
import unittest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db.models import User, Account, Merchant, Transaction, Subscription, Base
from db.config import Config

test_engine = create_engine(Config.TEST_SQLALCHEMY_DATABASE_URI)
# app.config['TESTING'] = True

sandbox_url = Config.TEST_PLAID_URL
client_id = Config.TEST_PLAID_CLIENT_ID
secret = Config.PLAID_SECRET
standard_header = {'Content-Type': 'application/json'}


class TestTableCreationOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.Session = sessionmaker(bind=test_engine)
        cls.test_file = open('./db/test_files/test_models.txt', 'r')

        cls.TYPE_MAPPINGS = {
            'DATETIME': lambda s: datetime.strptime(s, '%Y-%m-%d:%H:%M:%S'),
            'VARCHAR': str,
            'FLOAT': float
        }
        Base.metadata.drop_all(test_engine)
        Base.metadata.create_all(test_engine)

    @classmethod
    def tearDownClass(cls) -> None:
        # Base.metadata.drop_all(test_engine)
        cls.test_file.close()

    def setUp(self):
        self.session = self.Session()

    def tearDown(self):
        self.session.close()

    def get_next_line(self):
        cur_line = ''
        is_comment = True
        while is_comment:
            cur_line = self.test_file.readline().strip()
            if not cur_line:
                continue
            if cur_line:
                if cur_line[0] == '#':
                    is_comment = True
                    continue
            is_comment = False
        return cur_line
        
    def get_insert_data(self, table, N):
        res = []
        for _ in range(N):
            cur_line = self.get_next_line().split(' ')
            args_dict = {}
            for col, value in zip(table.__table__.columns, cur_line):
                cname = str(col.name)
                ctype = str(col.type)
                value = str(value)

                if 'VARCHAR' in ctype:
                    ctype = 'VARCHAR'

                mapped_value = self.TYPE_MAPPINGS[ctype](value)
                args_dict[cname] = mapped_value
            res.append(table(**args_dict))

        return res

    def test1_insert_users(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'user')
        users = self.get_insert_data(User, N)
        self.assertEqual(N, len(users))
        self.session.add_all(users)
        self.session.commit()

    def test2_insert_accounts(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'account')
        accounts = self.get_insert_data(Account, N)
        self.assertEqual(N, len(accounts))
        self.session.add_all(accounts)
        self.session.commit()

    def test3_insert_merchants(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'merchant')
        merchants = self.get_insert_data(Merchant, N)
        self.assertEqual(N, len(merchants))
        self.session.add_all(merchants)
        self.session.commit()

    def test4_insert_transactions(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'transaction')
        transactions = self.get_insert_data(Transaction, N)
        self.assertEqual(N, len(transactions))
        self.session.add_all(transactions)
        self.session.commit()

    # testing the cascading orphan delete setting
    def test5_orphan_delete(self):
        cur_user = self.session.get(User, '4')
        self.assertEqual(len(cur_user.accounts), 2)

        all_transactions = []
        for acc in cur_user.accounts:
            for transaction in acc.transactions:
                all_transactions.append(transaction)

        self.assertEqual(len(all_transactions), 3)
        self.session.delete(cur_user)
        self.session.commit()

        self.assertIsNone(self.session.get(User, '4'))
        smt = select(Transaction).where(Transaction.user_id == '4')
        t = self.session.scalars(smt).all()
        self.assertEqual(len(t), 0)
        smt = select(Account).where(Account.user_id == '4')
        a = self.session.scalars(smt).all()
        self.assertEqual(len(a), 0)

    # testing ORM object addition
    def test7_user_creation(self):
        user = User(
            user_id='user1',
            created_at=datetime.now(),
            user_first_name='John',
            user_last_name='Doe',
            user_email='john.doe@example.com'
        )
        self.session.add(user)
        self.session.commit()
        
        retrieved_user = self.session.get(User, 'user1')
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.user_first_name, 'John')

    # testing ORM object additions
    def test8_account_creation(self):
        account = Account(account_id='account1')
        cur_user = self.session.get(User, 'user1')
        cur_user.accounts.append(account)
        self.session.commit()

        smt = select(Account).where(Account.account_id == 'account1')
        a = self.session.scalars(smt).all()
        self.assertEqual(len(a), 1)

    # testing how to use backref
    def test9_transaction_creation(self):
        cur_user: User = self.session.get(User, 'user1')
        cur_account: Account = cur_user.accounts[0]
        cur_merchant: Merchant = self.session.scalar(select(Merchant).where(Merchant.merchant_id == '1'))
        transaction = Transaction(transaction_id='transaction1', authorized_date=datetime.now(), \
                                  amount=10, user=cur_user, account=cur_account, merchant=cur_merchant)
        self.session.add(transaction)
        self.session.commit()

        transaction: Transaction = self.session.get(Transaction, 'transaction1')
        self.assertListEqual(['user1', cur_account.account_id, cur_merchant.merchant_id],
                             [transaction.user_id, transaction.account_id, transaction.merchant_id])

    # testing the cascading delete on Account when User is deleted
    def test10_account_cascade_on_user_delete(self):
        user = User(user_id='user2', created_at=datetime.now(), user_first_name='Alice', user_last_name='Smith', user_email='alice.smith@example.com')
        account1 = Account(account_id='account2', user=user)
        account2 = Account(account_id='account3', user=user)
        self.session.add(user)
        self.session.add(account1)
        self.session.add(account2)
        self.session.commit()

        self.session.delete(user)
        self.session.commit()

        self.assertIsNone(self.session.get(User, 'user2'))
        self.assertIsNone(self.session.get(Account, 'account2'))
        self.assertIsNone(self.session.get(Account, 'account3'))

    # testing the addition of Transactions with existing Merchants and Accounts
    def test11_transaction_with_existing_references(self):
        user = User(user_id='user3', created_at=datetime.now(), user_first_name='Bob', user_last_name='Brown', user_email='bob.brown@example.com')
        account = Account(account_id='account4', user=user)
        merchant = Merchant(merchant_id='merchant1', merchant_name='SuperMart')
        self.session.add(user)
        self.session.add(account)
        self.session.add(merchant)
        self.session.commit()

        transaction = Transaction(
            transaction_id='transaction2',
            amount=25.0,
            authorized_date=datetime.now(),
            personal_finance_category='Electronics',
            user=user,
            account=account,
            merchant=merchant
        )
        self.session.add(transaction)
        self.session.commit()

        retrieved_transaction = self.session.get(Transaction, 'transaction2')
        self.assertEqual(retrieved_transaction.amount, 25.0)
        self.assertEqual(retrieved_transaction.user, user)
        self.assertEqual(retrieved_transaction.account, account)
        self.assertEqual(retrieved_transaction.merchant, merchant)

    # testing the creation and retrieval of Subscriptions
    def test12_subscription_creation_and_retrieval(self):
        user = User(user_id='user4', created_at=datetime.now(), user_first_name='Carol', user_last_name='White', user_email='carol.white@example.com')
        merchant = Merchant(merchant_id='merchant2', merchant_name='TechStore')
        self.session.add(user)
        self.session.add(merchant)
        self.session.commit()

        subscription = Subscription(
            subscription_id=1,
            name='Premium Service',
            price=99.99,
            renewal_date=datetime.now(),
            user=user,
            merchant=merchant
        )
        self.session.add(subscription)
        self.session.commit()

        retrieved_subscription = self.session.get(Subscription, 1)
        self.assertEqual(retrieved_subscription.name, 'Premium Service')
        self.assertEqual(retrieved_subscription.user, user)
        self.assertEqual(retrieved_subscription.merchant, merchant)

    # testing multiple transactions related to a single account
    def test13_multiple_transactions_for_account(self):
        user = User(user_id='user5', created_at=datetime.now(), user_first_name='Eve', user_last_name='Johnson', user_email='eve.johnson@example.com')
        account = Account(account_id='account5', user=user)
        self.session.add(user)
        self.session.add(account)
        self.session.commit()

        transaction1 = Transaction(transaction_id='transaction3', amount=45.0, authorized_date=datetime.now(), \
                                    personal_finance_category='Dining', account=account, user=user, merchant_id='merchant1')
        transaction2 = Transaction(transaction_id='transaction4', amount=60.0, authorized_date=datetime.now(), \
                                    personal_finance_category='Books', account=account, user=user, merchant_id='merchant1')
        self.session.add(transaction1)
        self.session.add(transaction2)
        self.session.commit()

        transactions = self.session.query(Transaction).filter_by(account_id='account5').all()
        self.assertEqual(len(transactions), 2)
        self.assertIn(transaction1, transactions)
        self.assertIn(transaction2, transactions)

if __name__ == '__main__':
    unittest.main()