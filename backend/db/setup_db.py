from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import argparse

def initialize_database(sqlalchemy_database_uri: str):
    from sqlalchemy import create_engine
    from db.models import Base
    engine = create_engine(sqlalchemy_database_uri)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Database initialized!")

def main():
    parser = argparse.ArgumentParser(
        prog="Initialize the FinanceTracker Database",
        description="Initialize the fintracker database",
    )
    parser.add_argument("--env_file", type=str, help="The .env file to use for deployment")
    args = parser.parse_args()

    environment_file = args.env_file

    load_dotenv(environment_file)

    class Settings(BaseSettings):
        sqlalchemy_database_uri: str

    settings = Settings()
    initialize_database(settings.sqlalchemy_database_uri)

if __name__ == "__main__":
    main()