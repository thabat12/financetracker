import httpx
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# yield_db
global_session = None
session_set = False

def set_global_session(new_global_session):
    global session_set
    if session_set:
        raise Exception('cannot change global_session during runtime!')
    global global_session
    global_session = new_global_session
    session_set = True

def get_global_session():
    return global_session

async def yield_db():
    global global_session
    if not global_session:
        raise Exception('there is no global session defined!')
    else:
        async with global_session() as session:
            yield session

async def yield_client():
    async with httpx.AsyncClient(timeout=30) as client:
        yield client