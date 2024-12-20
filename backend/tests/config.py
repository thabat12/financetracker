
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from tests.data.userdata import generate_random_mock_google_user
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.propagate = True

def override_google_login_response_dependency():
    logger.info("override_google_login_response_dependency")
    return generate_random_mock_google_user() # creates a random GoogleAuthUserInfo object