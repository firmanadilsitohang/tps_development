"""
Audit Trail Model - Track all CRUD operations.
"""
from . import db
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    """Model for audit trail logging."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64), nullable=True)  # Store username separately for historical records
    action = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    entity_type = db.Column(db.String(50), nullable=False)  # News, Training, Employee, etc.
    entity_id = db.Column(db.Integer, nullable=True)  # ID of affected record
    entity_name = db.Column(db.String(200), nullable=True)  # Name/title of affected record
    details = db.Column(db.Text, nullable=True)  # JSON string of changes
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<AuditLog {self.timestamp} - {self.username} - {self.action} {self.entity_type}>'

    @staticmethod
    def log(user_id, username, action, entity_type, entity_id=None, entity_name=None, details=None, ip_address=None, user_agent=None):
        """Create a new audit log entry."""
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
