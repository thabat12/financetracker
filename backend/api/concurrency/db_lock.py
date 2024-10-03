from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


async def acquire_db_session_lock(unique_key: str, session: AsyncSession):

    # map unique key to a positive integer for acquiring the lock
    unique_key = hash(unique_key) & 0x7fffffff

    await session.execute(text(f'SELECT pg_advisory_lock({unique_key});'))

async def release_db_session_lock(unique_key: str, session: AsyncSession):
    # map unique key to a positive integer for acquiring the lock
    unique_key = hash(unique_key) & 0x7fffffff
    await session.execute(text(f'SELECT pg_advisory_unlock({unique_key});'))