import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db, Base
from app.core.config import settings

# Since we must not destroy the dev DB, we'll connect to it but wrap tests in transactions
# Or we can use SQLite memory for tests if it's simpler, but the request says:
# "Use the project PostgreSQL environment appropriately."
# So we use the same postgres DB but run each test in a transaction that rolls back.

engine = create_engine(settings.database_url, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def setup_db():
    # Make sure tables exist in the db before running tests
    # In a real scenario Alembic would have run, but just in case we can create all
    # Though we don't want to drop all because it's the dev db!
    # So we DO NOT drop_all. We just rely on the existing schema created by Alembic.
    pass

@pytest.fixture()
def db_session(setup_db):
    """
    Creates a new database session with a rollback to avoid mutating dev DB.
    """
    connection = engine.connect()
    transaction = connection.begin()
    
    # bind an individual Session to the connection
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    # Rollback the transaction to prevent changes from persisting
    transaction.rollback()
    connection.close()

@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
