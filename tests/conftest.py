import pytest
from datetime import date

from app import create_app
from app.extensions import db
from app.models import Member, Package, Invoice, User

class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    LOGIN_DISABLED = False

@pytest.fixture
def app():
    application = create_app(TestConfig)
    
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session

@pytest.fixture
def sample_package(app):
    with app.app_context():
        package = Package(
            name="Test Package",
            duration_months=3,
            price=1200000,
            description="Test package description"
        )
        db.session.add(package)
        db.session.commit()
        return package.id

@pytest.fixture
def sample_user(app):
    with app.app_context():
        user = User(
            username="test_receptionist",
            email="test@example.com",
            role="receptionist"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user.id
