import os
import requests
import unittest
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

from api.app import app
from db.models import User, Account, Merchant, Transaction, Subscription, db
from db.config import Config

app.config['SQLALCHEMY_DATABASE_URI'] = Config.TEST_SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['TESTING'] = True

sandbox_url = Config.TEST_PLAID_URL
client_id = Config.TEST_PLAID_CLIENT_ID
secret = Config.PLAID_SECRET
standard_header = {'Content-Type': 'application/json'}


class TestTableCreationOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_context = app.app_context()
        cls.app_context = app_context
        cls.app_context.push()

        db.drop_all()
        db.create_all()

        cls.test_file = open('./db/test_files/test_models.txt', 'r')

        cls.TYPE_MAPPINGS = {
            'DATETIME': lambda s: datetime.strptime(s, '%Y-%m-%d:%H:%M:%S'),
            'VARCHAR': str,
            'FLOAT': float
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # db.drop_all()
        cls.app_context.pop()

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
        self.assertEqual(tablename, 'users')
        users = self.get_insert_data(User, N)
        self.assertEqual(N, len(users))
        db.session.add_all(users)
        db.session.commit()

    def test2_insert_accounts(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'accounts')
        accounts = self.get_insert_data(Account, N)
        self.assertEqual(N, len(accounts))
        db.session.add_all(accounts)
        db.session.commit()

    def test3_insert_merchants(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'merchant')
        merchants = self.get_insert_data(Merchant, N)
        self.assertEqual(N, len(merchants))
        db.session.add_all(merchants)
        db.session.commit()

    def test4_insert_transactions(self):
        action, tablename, N = self.get_next_line().split(' ')
        N = int(N)
        self.assertEqual(action, 'INSERT')
        self.assertEqual(tablename, 'transaction')
        transactions = self.get_insert_data(Transaction, N)
        self.assertEqual(N, len(transactions))
        db.session.add_all(transactions)
        db.session.commit()

    def test5_test_delete_accounts(self):
        # testing for cascade = all, delete-orphan settings
        cur_user = db.session.get(User, '2')
        print(cur_user.accounts)

        # print(accounts)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()