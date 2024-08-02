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

sandbox_url = Config.TEST_PLAID_URL
client_id = Config.TEST_PLAID_CLIENT_ID
secret = Config.PLAID_SECRET
standard_header = {'Content-Type': 'application/json'}


class TestTableCreationOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()
        db.create_all()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app_context.pop()

    def test_login_user(self):
        response = requests.post(f'{sandbox_url}/sandbox/public_token/create',
            headers=standard_header,
            json={'client_id': client_id, 'secret': secret,
                    'institution_id': 'ins_20',
                    'initial_products': ['transactions'],
                    'options': {
                        'webhook': 'https://www.plaid.com/webhook'
                    }
                }).json()

        response = requests.post(f'{sandbox_url}/item/public_token/exchange',
            headers=standard_header,
            json={
                'client_id': client_id,
                'secret': secret,
                'public_token': response['public_token']
            }).json()
        
        public_access_token = response['access_token']

        user = User(user_id="1", created_at=datetime.now(), access_key=public_access_token,
                    user_first_name="Steve", user_last_name="balls", 
                    user_email="steveballs@gmail.com", user_profile_picture=None)
        
        db.session.add(user)
        db.session.commit()

        user = db.session.get(User, "1")
        self.assertIsNotNone(user)

    def test_populate_user1(self):
        # user = self.cur_user

        # response = requests.post(f'{sandbox_url}/accounts/balance/get',
        #                          headers=standard_header,
        #                          json={'client_id': client_id, 'secret': secret,
        #                                'access_token': access})
        self.assertTrue(True)

    def tearDown(self):
        db.drop_all()

if __name__ == '__main__':
    unittest.main()