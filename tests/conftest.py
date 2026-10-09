"""
Pytest Test Fixtures and Environment Overrides
Configures an isolated in-memory or temporary SQLite database and temporary storage
to ensure complete test isolation without modifying development data.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.config import settings
from app.db.base import Base
from app.main import app

# Test Engine using a separate temporary database
TEST_DB_URL = "sqlite:///./test_data.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Sets up an isolated temporary storage directory for tests."""
    temp_storage = tmp_path_factory.mktemp("cert_storage")
    settings.STORAGE_DIR = temp_storage
    settings.RUN_WORKER_IN_APP = False  # Disable background thread in tests so we control worker ticks


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh, isolated database session per test function."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provides FastAPI TestClient with overridden get_db dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
