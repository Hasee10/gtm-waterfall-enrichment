import os

os.environ.setdefault("SQLITE_URI", ":memory:")
os.environ.setdefault("SQLITE_ASYNC_PREFIX", "sqlite+aiosqlite:///")

# Disable the testcontainers Ryuk reaper. Under `pytest -n auto`, each xdist worker
# is a separate process that spins up its own Ryuk container, and Docker Desktop
# chokes mapping all their ports at once ("Port mapping ... port 8080 is not
# available"). Testcontainers' own `with` blocks still clean up on normal exit.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import redis as syncredis  # noqa: E402
import redis.asyncio as aioredis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from testcontainers.core.docker_client import DockerClient  # noqa: E402

# mypy: disable-error-code="import-untyped"
from testcontainers.postgres import PostgresContainer  # noqa: E402

from src.infrastructure.database.session import Base, async_session  # noqa: E402
from src.interfaces.main import app  # noqa: E402

backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))


def is_docker_running() -> bool:
    try:
        DockerClient()
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(scope="session")
async def pg_container():
    """Create a PostgreSQL container for testing."""
    if not is_docker_running():
        pytest.skip("Docker is required, but not running")

    with PostgresContainer() as pg:
        yield pg


@pytest_asyncio.fixture(scope="function")
async def test_db_url(pg_container):
    """Create a proper asyncpg URL for PostgreSQL."""
    host = pg_container.get_container_host_ip()
    port_to_expose = 5432
    if hasattr(pg_container, "port_to_expose"):
        port_to_expose = pg_container.port_to_expose
    port = pg_container.get_exposed_port(port_to_expose)

    db = "test"
    user = "test"
    password = "test"
    if hasattr(pg_container, "POSTGRES_USER"):
        user = pg_container.POSTGRES_USER
    if hasattr(pg_container, "POSTGRES_PASSWORD"):
        password = pg_container.POSTGRES_PASSWORD
    if hasattr(pg_container, "POSTGRES_DB"):
        db = pg_container.POSTGRES_DB

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_db_url):
    """Create a SQLAlchemy engine for testing."""
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db(test_db_engine):
    """Create a test database session."""
    test_session = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
    async with test_session() as session:  # type: ignore
        yield session


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db):
    """Alias for test_db."""
    yield test_db


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """Create a test client with an overridden database session.

    The API has no auth, so there is no authenticated-client variant.
    """
    app.dependency_overrides = {}

    async def override_get_db():
        yield test_db

    app.dependency_overrides[async_session] = override_get_db

    os.environ["POSTGRES_SERVER"] = "localhost"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def patch_redis_pipeline_for_tests(monkeypatch):
    """Patch Redis pipeline so tests don't need a live Redis."""

    class MockPipeline:
        def __init__(self, *args, **kwargs):
            self.commands = []

        def execute(self, *args, **kwargs):
            return [True for _ in self.commands]

        async def aexecute(self, *args, **kwargs):
            return [True for _ in self.commands]

        def set(self, *args, **kwargs):
            self.commands.append(("set", args, kwargs))
            return self

        def sadd(self, *args, **kwargs):
            self.commands.append(("sadd", args, kwargs))
            return self

        def srem(self, *args, **kwargs):
            self.commands.append(("srem", args, kwargs))
            return self

        def expire(self, *args, **kwargs):
            self.commands.append(("expire", args, kwargs))
            return self

        def delete(self, *args, **kwargs):
            self.commands.append(("delete", args, kwargs))
            return self

    monkeypatch.setattr(aioredis.Redis, "pipeline", MockPipeline)
    monkeypatch.setattr(syncredis.Redis, "pipeline", MockPipeline)
