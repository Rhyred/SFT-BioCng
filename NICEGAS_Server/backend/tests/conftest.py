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

@pytest.fixture()
def test_user(db_session):
    import uuid
    from app.models.user import User
    from app.core.security import hash_password
    
    user = User(
        id=uuid.uuid4(),
        username="test_operator",
        email="test_operator@nicegas.local",
        name="Test Operator",
        role="operator",
        hashed_password=hash_password("test_pass_123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture()
def admin_user(db_session):
    import uuid
    from app.models.user import User
    from app.core.security import hash_password
    
    user = User(
        id=uuid.uuid4(),
        username="test_admin",
        email="test_admin@nicegas.local",
        name="Test Admin",
        role="admin",
        hashed_password=hash_password("test_admin_pass"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture()
def auth_headers(test_user):
    from app.core.security import create_access_token
    token = create_access_token({
        "sub": str(test_user.id),
        "role": test_user.role,
        "name": test_user.name,
        "email": test_user.email,
        "username": test_user.username,
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def admin_auth_headers(admin_user):
    from app.core.security import create_access_token
    token = create_access_token({
        "sub": str(admin_user.id),
        "role": admin_user.role,
        "name": admin_user.name,
        "email": admin_user.email,
        "username": admin_user.username,
    })
    return {"Authorization": f"Bearer {token}"}
