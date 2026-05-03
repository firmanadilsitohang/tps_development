"""
Service layer for Training Schedule operations.
"""
from datetime import datetime, timezone
from app import db
from app.models.development import Training


class TrainingService:
    """Business logic for Training operations."""

    @staticmethod
    def get_all_trainings():
        """Get all trainings ordered by date (newest first)."""
        return Training.query.order_by(Training.training_date.desc()).all()

    @staticmethod
    def get_training_by_id(training_id):
        """Get training by ID."""
        return Training.query.get(training_id)

    @staticmethod
    def get_upcoming_trainings():
        """Get upcoming trainings (future dates)."""
        return Training.query.filter(
            Training.training_date >= datetime.now(timezone.utc)
        ).order_by(Training.training_date.asc()).all()

    @staticmethod
    def _sanitize(data):
        """Sanitize input data to prevent XSS."""
        from app.services.security import sanitize_text, sanitize_html
        return {
            'title': sanitize_text(data.get('title', ''), 150),
            'description': sanitize_html(data.get('description', '')),
            'training_date': data.get('training_date', ''),
            'location': sanitize_text(data.get('location', ''), 100),
            'quota': data.get('quota', 0)
        }

    @staticmethod
    def create_training(data):
        """
        Create new training from data dictionary.
        Returns (success: bool, training: Training or None, message: str)
        """
        try:
            data = TrainingService._sanitize(data)
            # Parse date
            training_date_str = data.get('training_date')
            training_date = None

            if training_date_str:
                for fmt in ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                    try:
                        training_date = datetime.strptime(training_date_str, fmt)
                        break
                    except ValueError:
                        continue

            if training_date is None:
                return False, None, "Invalid date format"

            training = Training(
                title=data.get('title'),
                description=data.get('description', ''),
                training_date=training_date,
                location=data.get('location', ''),
                quota=int(data.get('quota', 0)) if data.get('quota') else 0
            )
            db.session.add(training)
            db.session.commit()
            return True, training, "Training created successfully"
        except Exception as e:
            db.session.rollback()
            return False, None, str(e)

    @staticmethod
    def update_training(training, data):
        """
        Update existing training with data dictionary.
        Returns (success: bool, message: str)
        """
        try:
            data = TrainingService._sanitize(data)
            if 'title' in data:
                training.title = data['title']
            if 'description' in data:
                training.description = data['description']
            if 'location' in data:
                training.location = data['location']
            if 'quota' in data:
                training.quota = int(data['quota']) if data['quota'] else 0

            if 'training_date' in data:
                training_date_str = data['training_date']
                for fmt in ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                    try:
                        training.training_date = datetime.strptime(training_date_str, fmt)
                        break
                    except ValueError:
                        continue

            db.session.commit()
            return True, "Training updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete_training(training):
        """
        Delete training.
        Returns (success: bool, message: str)
        """
        try:
            db.session.delete(training)
            db.session.commit()
            return True, "Training deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)
