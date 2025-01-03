from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    api_hostname: str
    postgres_hostname: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    async_sqlalchemy_database_uri: str
    sqlalchemy_database_uri: str
    alembic_config: str
    plaid_url: str
    plaid_client_id: str
    plaid_secret: str
    api_host: str
    api_port: int
    auth_secret_key: str
    db_secret_key: str

settings: BaseSettings = None

def set_global_settings(environment_filepath: str) -> None:
    global settings
    load_dotenv(dotenv_path=environment_filepath)
    settings = Settings()