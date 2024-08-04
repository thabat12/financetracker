import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PLAID_SECRET = os.environ.get('PLAID_SECRET') or 'a_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or 'sqlite:///financetracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
