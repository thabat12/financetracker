from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import shutil
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    sqlalchemy_database_uri: str

settings = Settings()

print('sqlalchemy_database_uri', settings.sqlalchemy_database_uri)


if __name__ == '__main__':
    # reset the alembic current version table
    db_engine = create_engine(settings.sqlalchemy_database_uri)

    try:
        with db_engine.connect() as connection:
            connection.execute(text('TRUNCATE TABLE alembic_version;'))
            connection.commit()
    except Exception as e:
        print('Resetting alembic version table failed!')
        raise e