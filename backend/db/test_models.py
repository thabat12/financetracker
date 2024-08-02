import os
import requests
import unittest
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

from db.models import User, Account, Merchant, Transaction, Subscription
from db.config import Config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.TEST_SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.app_context.pop()

    def setUp(self):
        db.create_all()

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
                    user_first_name="Steve", user_last_name="balls", user_email="steveballs@gmail.com",
                    user_profile_picture=None)
        
        self.cur_user = user



    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()