import os
import requests
import unittest
from datetime import datetime

from sqlalchemy import create_engine
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
        Base.metadata.drop_all(test_engine)
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

    def test5_open_transactions(self):
        # testing for cascade = all, delete-orphan settings
        new_usr = User(user_id='15', created_at=datetime(2010, 1, 1), access_key='1',
                       user_first_name='abhinav', user_last_name='bichal', user_email='hi',
                       user_profile_picture='picture.jpg')
        self.session.add(new_usr)

if __name__ == '__main__':
    unittest.main()