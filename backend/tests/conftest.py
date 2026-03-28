import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db

# Import all models to ensure they're registered on Base
import app.models.database_models  # noqa: F401

# Create a test engine
TEST_ENGINE = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Create a FastAPI test client with the test database."""
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
