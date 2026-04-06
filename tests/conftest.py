"""
Shared pytest fixtures for IPTVSur Portal tests.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.middlewares.auth import hash_password
from src.api.models.admin_user import AdminUser
from src.core.database import Base, get_db
from src.main import app

# ── In-memory SQLite for tests ────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

TEST_ADMIN_USERNAME = "admin"
TEST_ADMIN_PASSWORD = "testpassword"


async def override_get_db():
    """Replace the real DB with an in-memory one for every test."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app with the test DB."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_admin():
    """Insert a test admin user into the in-memory DB."""
    async with TestingSessionLocal() as session:
        user = AdminUser(
            username=TEST_ADMIN_USERNAME,
            hashed_password=hash_password(TEST_ADMIN_PASSWORD),
        )
        session.add(user)
        await session.commit()


@pytest.fixture
async def auth_client(client: AsyncClient, seed_admin) -> AsyncClient:
    """Authenticated client — carries a valid JWT Bearer header."""
    response = await client.post(
        "/api/admin/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
