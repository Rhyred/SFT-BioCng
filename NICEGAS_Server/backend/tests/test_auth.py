import uuid
from datetime import timedelta
import pytest
import jwt
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.auth import auth_service
from app.core.config import settings

def test_user_model_creation(db_session):
    """Verify User model can be persisted and queried."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test_model@nicegas.local",
        username="test_model_user",
        hashed_password=hash_password("secure_pass_123"),
        name="Model User",
        role="operator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    queried = db_session.query(User).filter_by(id=user_id).first()
    assert queried is not None
    assert queried.username == "test_model_user"
    assert queried.email == "test_model@nicegas.local"
    assert queried.role == "operator"
    assert queried.is_active is True

def test_password_hashing():
    """Verify bcrypt password hashing generates valid hashes and verifies properly."""
    plain = "mySecretPassword123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$2b$")
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_jwt_creation_and_decoding():
    """Verify JWT access token creation and decoding."""
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "role": "admin",
        "name": "Admin User",
        "email": "admin@nicegas.local",
        "username": "admin"
    }
    token = create_access_token(payload, expires_delta=timedelta(minutes=30))
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded["sub"] == user_id
    assert decoded["role"] == "admin"
    assert decoded["name"] == "Admin User"
    assert "exp" in decoded
    assert "iat" in decoded

def test_jwt_expiration():
    """Verify expired JWT is rejected."""
    user_id = str(uuid.uuid4())
    payload = {"sub": user_id, "role": "operator"}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)

def test_login_success_with_username(client, test_user):
    """Verify login with username returns token and user profile matching contract."""
    response = client.post("/auth/login", json={
        "username": "test_operator",
        "password": "test_pass_123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["id"] == str(test_user.id)
    assert data["user"]["name"] == "Test Operator"
    assert data["user"]["role"] == "operator"
    assert "hashed_password" not in data["user"]

def test_login_success_with_email(client, test_user):
    """Verify login with email returns token and user profile."""
    response = client.post("/auth/login", json={
        "email": "test_operator@nicegas.local",
        "password": "test_pass_123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["id"] == str(test_user.id)

def test_login_invalid_password(client, test_user):
    """Verify login with wrong password returns 401."""
    response = client.post("/auth/login", json={
        "username": "test_operator",
        "password": "wrong_password"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "INVALID_CREDENTIALS"

def test_login_unknown_user(client):
    """Verify login with non-existent user returns 401."""
    response = client.post("/auth/login", json={
        "username": "non_existent_user",
        "password": "some_password"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "INVALID_CREDENTIALS"

def test_login_inactive_user(client, db_session):
    """Verify login with disabled user returns 403."""
    user = User(
        id=uuid.uuid4(),
        username="disabled_operator",
        email="disabled@nicegas.local",
        name="Disabled User",
        role="operator",
        hashed_password=hash_password("disabled_pass"),
        is_active=False
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/auth/login", json={
        "username": "disabled_operator",
        "password": "disabled_pass"
    })
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["code"] == "INACTIVE_USER"

def test_auth_me_endpoint(client, auth_headers, test_user):
    """Verify GET /auth/me returns current user profile."""
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["username"] == "test_operator"
    assert data["email"] == "test_operator@nicegas.local"

def test_protected_endpoint_without_token(client):
    """Verify protected endpoints reject requests without token with 401."""
    response = client.get("/projects")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "UNAUTHORIZED"

def test_protected_endpoint_with_invalid_token(client):
    """Verify protected endpoints reject requests with invalid token."""
    response = client.get("/projects", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "INVALID_TOKEN"

def test_protected_endpoint_with_expired_token(client, test_user):
    """Verify protected endpoints reject requests with expired token."""
    expired_token = create_access_token(
        {"sub": str(test_user.id), "role": test_user.role},
        expires_delta=timedelta(seconds=-10)
    )
    response = client.get("/projects", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "TOKEN_EXPIRED"

def test_health_endpoint_is_public(client):
    """Verify GET /health remains public without requiring authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_seed_idempotency(db_session):
    """Verify running seed logic multiple times does not fail or duplicate users."""
    from seed_data import seed_data
    # Run seed_data against db_session/engine
    seed_data()
    # Count admin users
    admin_count = db_session.query(User).filter_by(username="admin").count()
    assert admin_count == 1
    # Run again
    seed_data()
    admin_count_2 = db_session.query(User).filter_by(username="admin").count()
    assert admin_count_2 == 1
