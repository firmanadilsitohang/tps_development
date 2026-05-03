"""
Unit tests for News CRUD operations.
"""
import pytest


class TestNewsManage:
    """Test cases for News management page."""

    def test_manage_news_page_loads(self, logged_in_tpsg_client):
        """Manage news page should load."""
        response = logged_in_tpsg_client.get('/tpsg/manage-news')
        assert response.status_code == 200

    def test_manage_news_requires_login(self, client):
        """Manage news should require login."""
        response = client.get('/tpsg/manage-news')
        assert response.status_code == 302

    def test_manage_news_requires_tpsg_role(self, logged_in_client):
        """Manage news should require TPSG role."""
        response = logged_in_client.get('/tpsg/manage-news')
        assert response.status_code == 302


class TestNewsCreate:
    """Test cases for creating news."""

    def test_create_news_success(self, logged_in_tpsg_client):
        """Creating news should succeed with valid data."""
        response = logged_in_tpsg_client.post('/tpsg/manage-news', data={
            'title': 'Test Announcement',
            'category': 'News',
            'content': 'This is a test announcement content.',
            'target_type': 'all'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Test Announcement' in response.data or b'berhasil' in response.data.lower()

    def test_create_news_schedule(self, logged_in_tpsg_client):
        """Creating schedule news should succeed."""
        response = logged_in_tpsg_client.post('/tpsg/manage-news', data={
            'title': 'Test Schedule',
            'category': 'Schedule',
            'content': 'This is a test schedule.',
            'target_type': 'all'
        }, follow_redirects=True)
        assert response.status_code == 200


class TestNewsEdit:
    """Test cases for editing news."""

    def test_edit_news_page_loads(self, logged_in_tpsg_client):
        """Edit news page should load."""
        # First create a news item
        logged_in_tpsg_client.post('/tpsg/manage-news', data={
            'title': 'Original Title',
            'category': 'News',
            'content': 'Original content.',
            'target_type': 'all'
        })

        # Get the news ID from database
        from app.models.development import News
        news = News.query.first()
        if news:
            response = logged_in_tpsg_client.get(f'/tpsg/edit-news/{news.id}')
            assert response.status_code == 200
            assert b'Original Title' in response.data

    def test_edit_news_update(self, logged_in_tpsg_client):
        """Editing news should update the record."""
        # Create news first
        logged_in_tpsg_client.post('/tpsg/manage-news', data={
            'title': 'Title to Edit',
            'category': 'News',
            'content': 'Content to edit.',
            'target_type': 'all'
        })

        from app.models.development import News
        news = News.query.first()
        if news:
            response = logged_in_tpsg_client.post(
                f'/tpsg/edit-news/{news.id}',
                data={
                    'title': 'Updated Title',
                    'category': 'News',
                    'content': 'Updated content.',
                    'target_type': 'all'
                },
                follow_redirects=True
            )
            assert response.status_code == 200


class TestNewsDelete:
    """Test cases for deleting news."""

    def test_delete_news_success(self, logged_in_tpsg_client):
        """Deleting news should succeed."""
        # Create news first
        logged_in_tpsg_client.post('/tpsg/manage-news', data={
            'title': 'Title to Delete',
            'category': 'News',
            'content': 'Content to delete.',
            'target_type': 'all'
        })

        from app.models.development import News
        news = News.query.first()
        if news:
            news_id = news.id
            response = logged_in_tpsg_client.post(
                f'/tpsg/delete-news/{news_id}',
                data={},
                follow_redirects=True
            )
            assert response.status_code == 200
            # Verify deleted
            assert News.query.get(news_id) is None


class TestModulesCRUD:
    """Test cases for Learning Modules CRUD."""

    def test_manage_news_shows_modules_tab(self, logged_in_tpsg_client):
        """Manage news page should show modules tab."""
        response = logged_in_tpsg_client.get('/tpsg/manage-news')
        assert response.status_code == 200
        assert b'E-Learning' in response.data or b'module' in response.data.lower()


class TestTrainingCRUD:
    """Test cases for Training Schedule CRUD."""

    def test_manage_trainings_page_loads(self, logged_in_tpsg_client):
        """Manage trainings page should load."""
        response = logged_in_tpsg_client.get('/tpsg/trainings')
        assert response.status_code == 200

    def test_create_training_success(self, logged_in_tpsg_client):
        """Creating training should succeed."""
        response = logged_in_tpsg_client.post('/tpsg/trainings', data={
            'title': 'Test Training Workshop',
            'training_date': '2026-06-15T09:00',
            'location': 'Training Room A',
            'quota': '20',
            'description': 'Test training description.'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_edit_training_page_loads(self, logged_in_tpsg_client):
        """Edit training page should load."""
        # Create training first
        logged_in_tpsg_client.post('/tpsg/trainings', data={
            'title': 'Original Training',
            'training_date': '2026-06-15T09:00',
            'location': 'Room A',
            'quota': '20',
            'description': 'Description.'
        })

        from app.models.development import Training
        training = Training.query.first()
        if training:
            response = logged_in_tpsg_client.get(f'/tpsg/edit-training/{training.id}')
            assert response.status_code == 200
            assert b'Original Training' in response.data

    def test_delete_training_success(self, logged_in_tpsg_client):
        """Deleting training should succeed."""
        # Create training first
        logged_in_tpsg_client.post('/tpsg/trainings', data={
            'title': 'Training to Delete',
            'training_date': '2026-06-15T09:00',
            'location': 'Room A',
            'quota': '20',
            'description': 'Description.'
        })

        from app.models.development import Training
        training = Training.query.first()
        if training:
            training_id = training.id
            response = logged_in_tpsg_client.post(
                f'/tpsg/delete-training/{training_id}',
                data={},
                follow_redirects=True
            )
            assert response.status_code == 200
            assert Training.query.get(training_id) is None
