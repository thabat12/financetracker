import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text


async def acquire_db_transaction_lock(unique_key: str, session: AsyncSession):
    '''
        Acquire a database transaction lock using an advisory lock.
        Note that this lock is automatically released after a transaction.

        Args:
            unique_key (str): The unique key to use for the advisory lock.
            session (AsyncSession): The SQLAlchemy async session.

        Returns:
            None
    '''
    # hashlib provides with consistent hashing, which can be used to get a unique integer key
    unique_key = hashlib.sha256(unique_key.encode())
    unique_key = int.from_bytes(unique_key.digest(), byteorder='big') & 0x7fffffff

    await session.execute(text(f'SELECT pg_advisory_xact_lock({unique_key});'))

async def acquire_db_session_lock(unique_key: str, session: AsyncSession):
    '''
        Acquire a database session lock using an advisory lock.

        Args:
            unique_key (str): The unique key to use for the advisory lock.
            session (AsyncSession): The SQLAlchemy async session.

        Returns:
            None
    '''
    # hashlib provides with consistent hashing, which can be used to get a unique integer key
    unique_key = hashlib.sha256(unique_key.encode())
    unique_key = int.from_bytes(unique_key.digest(), byteorder='big') & 0x7fffffff

    await session.execute(text(f'SELECT pg_advisory_lock({unique_key});'))


async def release_db_session_lock(unique_key: str, session: AsyncSession):
    '''
        Release a previously acquired database session lock.

        Args:
            unique_key (str): The unique key used for the advisory lock.
            session (AsyncSession): The SQLAlchemy async session.

        Returns:
            None
    '''
    # map unique key to a positive integer for acquiring the lock
    unique_key = hashlib.sha256(unique_key.encode())
    unique_key = int.from_bytes(unique_key.digest(), byteorder='big') & 0x7fffffff

    await session.execute(text(f'SELECT pg_advisory_unlock({unique_key});'))