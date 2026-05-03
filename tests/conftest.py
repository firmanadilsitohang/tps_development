"""
Pytest configuration and fixtures for TPS-G tests.
"""
import os
import sys
import pytest
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('FLASK_ENV', 'testing')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-testing')

from app import create_app, db
from app.models.user import User
from app.models.employee import Employee, Plant, Division, Department
from app.models.development import News, Training
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    from app import db

    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for easier testing
        'SECRET_KEY': 'test-secret-key',
        'LOGIN_DISABLED': False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Provide a database session for tests."""
    with app.app_context():
        yield db.session


@pytest.fixture
def plant(app, db_session):
    """Create a test plant."""
    with app.app_context():
        plant = Plant(name='Sunter 1')
        db_session.add(plant)
        db_session.commit()
        return plant


@pytest.fixture
def division(app, db_session):
    """Create a test division."""
    with app.app_context():
        div = Division(name='HO')
        db_session.add(div)
        db_session.commit()
        return div


@pytest.fixture
def department(app, db_session):
    """Create a test department."""
    with app.app_context():
        dept = Department(name='TPS-G')
        db_session.add(dept)
        db_session.commit()
        return dept


@pytest.fixture
def test_employee(app, db_session, plant, division, department):
    """Create a test employee."""
    with app.app_context():
        emp = Employee(
            username='12345678',
            name='Test Employee',
            birth_date=date(1990, 1, 1),
            position='Group Leader',
            current_tps_level='TPS ADVANCE',
            status='active',
            plant_id=plant.id,
            division_id=division.id,
            department_id=department.id
        )
        db_session.add(emp)
        db_session.commit()
        return emp


@pytest.fixture
def test_user(app, db_session, test_employee):
    """Create a test user (participant role)."""
    with app.app_context():
        user = User(
            username='12345678',
            password=generate_password_hash('password123'),
            role='participant',
            employee_id=test_employee.id
        )
        db_session.add(user)
        db_session.commit()
        return user


@pytest.fixture
def tpsg_user(app, db_session):
    """Create a TPSG admin user."""
    with app.app_context():
        user = User(
            username='ADMIN001',
            password=generate_password_hash('admin123'),
            role='tpsg'
        )
        db_session.add(user)
        db_session.commit()
        return user


@pytest.fixture
def omdd_user(app, db_session):
    """Create an OMDD assessor user."""
    with app.app_context():
        user = User(
            username='OMDD001',
            password=generate_password_hash('omdd123'),
            role='omdd'
        )
        db_session.add(user)
        db_session.commit()
        return user


@pytest.fixture
def management_user(app, db_session):
    """Create a management user."""
    with app.app_context():
        user = User(
            username='MGMT001',
            password=generate_password_hash('mgmt123'),
            role='management'
        )
        db_session.add(user)
        db_session.commit()
        return user


@pytest.fixture
def logged_in_client(client, test_user):
    """A logged-in test client (participant)."""
    client.post('/auth/login', data={
        'username': '12345678',
        'password': 'password123'
    })
    return client


@pytest.fixture
def logged_in_tpsg_client(client, tpsg_user):
    """A logged-in test client (TPSG admin)."""
    client.post('/auth/login', data={
        'username': 'ADMIN001',
        'password': 'admin123'
    })
    return client


@pytest.fixture
def logged_in_omdd_client(client, omdd_user):
    """A logged-in test client (OMDD)."""
    client.post('/auth/login', data={
        'username': 'OMDD001',
        'password': 'omdd123'
    })
    return client


@pytest.fixture
def logged_in_mgmt_client(client, management_user):
    """A logged-in test client (Management)."""
    client.post('/auth/login', data={
        'username': 'MGMT001',
        'password': 'mgmt123'
    })
    return client
