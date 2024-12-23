# conftest.py

import pytest
from sqlalchemy import create_engine, text
from api.config import settings

engine = create_engine(settings.test_sqlalchemy_database_uri)

@pytest.fixture
def clear_database(scope="function"):
    print("clearing database before running tests...")
    conn = engine.connect()
    conn.execute(text("TRUNCATE TABLE financetracker_user CASCADE;"))
    conn.execute(text("TRUNCATE TABLE institution CASCADE;"))
    conn.commit()
    print("database cleared")
    conn.close()
