"""Shared pytest fixtures for API tests and database isolation."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.context import CryptContext
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core import security
from app.core.config import settings
from app.db.base_class import Base
from app.main import app


@pytest.fixture(autouse=True)
def _use_plaintext_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "pwd_context", CryptContext(schemes=["plaintext"]))


@pytest_asyncio.fixture()
async def session() -> AsyncSession:
    database_url = settings.test_database_url or settings.database_url
    url = make_url(database_url)
    schema_name: str | None = None
    engine = create_async_engine(database_url, future=True)
    if url.drivername.startswith("postgresql"):
        # Isolate each test run in its own schema for parallel-friendly cleanup.
        schema_name = f"test_{uuid.uuid4().hex}"
        engine = engine.execution_options(schema_translate_map={None: schema_name})
    async with engine.begin() as conn:
        if schema_name:
            await conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        await conn.run_sync(Base.metadata.create_all)
    TestingSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with TestingSession() as session:
            yield session
    finally:
        async with engine.begin() as conn:
            if schema_name:
                await conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            else:
                await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncClient:
    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_db, None)
