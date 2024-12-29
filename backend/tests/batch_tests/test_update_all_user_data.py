import pytest

from db.models import *

from tests.config import clear

async def test_update_all_user_data_simple(clear_database):
    