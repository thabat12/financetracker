from pydantic import BaseModel
from pydantic_settings import BaseSettings
from fastapi import APIRouter, HTTPException, Header
import httpx

from batch.config import Session, async_database_engine, settings, yield_db
from batch.routes.auth import verify_token
from db.models import *

data_router = APIRouter()

@data_router.post('/get_transactions')
def get_transactions(authorization: str = Header(...)):
    pass