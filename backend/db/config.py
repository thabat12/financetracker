import os

from dotenv import load_dotenv
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    TEST_SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_SQLALCHEMY_DATABASE_URI')
    TEST_PLAID_URL = os.environ.get('TEST_PLAID_URL')
    TEST_PLAID_CLIENT_ID = os.environ.get('TEST_PLAID_CLIENT_ID')
    PLAID_SECRET = os.environ.get('PLAID_SECRET')