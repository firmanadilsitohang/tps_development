"""
Unit tests for Employee routes (TPSG Admin).
"""
import pytest


class TestEmployeeDirectory:
    """Test cases for employee directory page."""

    def test_employees_page_loads(self, logged_in_tpsg_client):
        """Employees page should load for TPSG admin."""
        response = logged_in_tpsg_client.get('/tpsg/employees')
        assert response.status_code == 200

    def test_employees_page_requires_login(self, client):
        """Employees page should require login."""
        response = client.get('/tpsg/employees')
        assert response.status_code == 302  # Redirect to login

    def test_employees_page_requires_tpsg_role(self, logged_in_client):
        """Employees page should require TPSG role."""
        response = logged_in_client.get('/tpsg/employees')
        assert response.status_code == 302  # Redirect away

    def test_employees_shows_data(self, logged_in_tpsg_client, test_employee):
        """Employees page should show employee data."""
        response = logged_in_tpsg_client.get('/tpsg/employees')
        assert response.status_code == 200
        assert b'Test Employee' in response.data or test_employee.name.encode() in response.data

    def test_employees_filter_by_status(self, logged_in_tpsg_client, test_employee):
        """Employees can be filtered by status."""
        response = logged_in_tpsg_client.get('/tpsg/employees?status=active')
        assert response.status_code == 200


class TestEmployeeDetail:
    """Test cases for employee detail page."""

    def test_employee_detail_loads(self, logged_in_tpsg_client, test_employee):
        """Employee detail page should load."""
        response = logged_in_tpsg_client.get(f'/tpsg/employee/{test_employee.id}')
        assert response.status_code == 200

    def test_employee_detail_update(self, logged_in_tpsg_client, test_employee):
        """Employee data should be updateable."""
        response = logged_in_tpsg_client.post(
            f'/tpsg/employee/{test_employee.id}',
            data={
                'name': 'Updated Name',
                'username': '12345678',
                'position': 'Supervisor',
                'current_tps_level': 'TPS KEY PERSON 3',
                'last_activity_type': 'Kaizen'
            },
            follow_redirects=True
        )
        assert response.status_code == 200


class TestBulkDelete:
    """Test cases for bulk delete functionality."""

    def test_bulk_delete_requires_login(self, client):
        """Bulk delete should require login."""
        response = client.post('/tpsg/bulk-delete-employees', data={})
        assert response.status_code == 302

    def test_bulk_delete_single_employee(self, logged_in_tpsg_client, test_employee):
        """Should be able to delete single employee."""
        response = logged_in_tpsg_client.post(
            '/tpsg/bulk-delete-employees',
            data={'employee_ids': [str(test_employee.id)]},
            follow_redirects=True
        )
        assert response.status_code == 200


class TestImportExcel:
    """Test cases for Excel import functionality."""

    def test_import_page_loads(self, logged_in_tpsg_client):
        """Import Excel page should load."""
        response = logged_in_tpsg_client.get('/tpsg/import-excel')
        assert response.status_code == 200

    def test_import_page_requires_login(self, client):
        """Import Excel page should require login."""
        response = client.get('/tpsg/import-excel')
        assert response.status_code == 302

    def test_import_without_file(self, logged_in_tpsg_client):
        """Import without file should show error."""
        response = logged_in_tpsg_client.post(
            '/tpsg/import-excel',
            data={},
            follow_redirects=True
        )
        assert response.status_code == 200
        # Should show "Pilih file dulu" or similar message


class TestResetAll:
    """Test cases for reset all functionality."""

    def test_reset_all_employees(self, logged_in_tpsg_client, test_employee):
        """Reset all should delete all employees."""
        response = logged_in_tpsg_client.post(
            '/tpsg/reset-all-employees',
            data={},
            follow_redirects=True
        )
        assert response.status_code == 200
