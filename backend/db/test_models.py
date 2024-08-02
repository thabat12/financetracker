import os
from dotenv import load_dotenv
import requests
import unittest
from db.models import User, Account, Merchant, Transaction, Subscription
from db.config import Config

load_dotenv()

TEST_SQLALCHEMY_DATABASE_URI = os.getenv('TEST_SQLALCHEMY_DATABASE_URI')

class TestTableCreationOperations(unittest.TestCase):
    def setUp(self):
        pass

    def test_create_models(self):
        pass

    def tearDown(self):
        pass