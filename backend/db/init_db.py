from db.models import User, Account, Merchant, Transaction, Subscription, Base
from db.config import Config

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
