from enum import Enum
import asyncio
from pydantic import BaseModel
from logging import Logger
from fastapi import APIRouter, HTTPException, Header
from sqlalchemy import select, update, case, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from api.config import settings, logger
from api.api_utils.auth_util import verify_token
from api.crypto.crypto import db_key_bytes, encrypt_data, decrypt_data, encrypt_float, decrypt_float
from db.models import *


data_router = APIRouter()

'''
    returns a list of list of plaid account: new, updated, deleted

'''        

'''
    returns a list of 3 elements of plaidtransaction objects: added, modified, removed

'''
