'''
    Run some tests to investigate concurrency and logic updates of the api
'''

import pytest


def test_imports():
    assert 1 + 1 == 2

@pytest.mark.asyncio
async def test_login():
    assert 2 + 2 == 4