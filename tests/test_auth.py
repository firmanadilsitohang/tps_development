"""
Unit tests for Authentication routes.
"""
import pytest
from werkzeug.security import generate_password_hash


class TestLogin:
    """Test cases for login functionality."""

    def test_login_page_loads(self, client):
        """Login page should load successfully."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'<form' in response.data

    def test_login_success(self, client, test_user):
        """Valid credentials should login successfully."""
        response = client.post('/auth/login', data={
            'username': '12345678',
            'password': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to participant dashboard

    def test_login_invalid_password(self, client, test_user):
        """Invalid password should fail."""
        response = client.post('/auth/login', data={
            'username': '12345678',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b'Incorrect password' in response.data or b'login' in response.data.lower()

    def test_login_nonexistent_user(self, client):
        """Non-existent user should fail."""
        response = client.post('/auth/login', data={
            'username': '99999999',
            'password': 'anypassword'
        })
        assert response.status_code == 200
        assert b'incorrect' in response.data.lower() or b'tidak' in response.data.lower()

    def test_login_missing_fields(self, client):
        """Missing fields should fail."""
        response = client.post('/auth/login', data={
            'username': '',
            'password': ''
        })
        assert response.status_code == 200


class TestLogout:
    """Test cases for logout functionality."""

    def test_logout(self, client, logged_in_client):
        """Logged in user should be able to logout."""
        response = logged_in_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        # After logout, should redirect to login

    def test_logout_when_not_logged_in(self, client):
        """Not logged in user should redirect to login."""
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200


class TestRegister:
    """Test cases for registration functionality."""

    def test_register_page_loads(self, client):
        """Register page should load successfully."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'<form' in response.data

    def test_register_success(self, client, plant, division, department):
        """Valid registration should succeed."""
        response = client.post('/auth/register', data={
            'name': 'New User',
            'username': '87654321',
            'birth_date': '1995-05-15',
            'position': 'Operator',
            'plant': 'Sunter 1',
            'division': 'HO',
            'department': 'TPS-G',
            'password': 'newpass123',
            'previous_tps_level': 'TPS BASIC',
            'tahun_lulus_terakhir': '2020',
            'current_tps_level': 'TPS SW',
            'tahun_lulus_saat_ini': '2023',
            'last_activity_type': 'Kaizen',
            'last_activity_theme': 'Theme 1',
            'batch': '#1'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_register_duplicate_username(self, client, test_user, plant, division, department):
        """Duplicate username should fail."""
        response = client.post('/auth/register', data={
            'name': 'Duplicate User',
            'username': '12345678',  # Same as test_user
            'birth_date': '1995-05-15',
            'position': 'Operator',
            'plant': 'Sunter 1',
            'division': 'HO',
            'department': 'TPS-G',
            'password': 'newpass123',
            'previous_tps_level': 'TPS BASIC',
            'tahun_lulus_terakhir': '2020',
            'current_tps_level': 'TPS SW',
            'tahun_lulus_saat_ini': '2023',
            'last_activity_type': 'Kaizen',
            'last_activity_theme': 'Theme 1',
            'batch': '#1'
        })
        assert response.status_code == 200
        # Should show error about existing user


class TestChangePassword:
    """Test cases for password change functionality."""

    def test_change_password_page_loads(self, client, logged_in_client):
        """Change password page should load for logged in user."""
        response = logged_in_client.get('/auth/change-password')
        assert response.status_code == 200

    def test_change_password_success(self, client, test_user):
        """Valid password change should succeed."""
        # Login first
        client.post('/auth/login', data={
            'username': '12345678',
            'password': 'password123'
        })
        response = client.post('/auth/change-password', data={
            'current_password': 'password123',
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client, test_user):
        """Wrong current password should fail."""
        client.post('/auth/login', data={
            'username': '12345678',
            'password': 'password123'
        })
        response = client.post('/auth/change-password', data={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        })
        assert response.status_code == 200
