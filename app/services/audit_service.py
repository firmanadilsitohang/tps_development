"""
Audit Service - Provides functions to log CRUD operations.
"""
import json
from flask import request
from flask_login import current_user


class AuditService:
    """Service for creating audit trail logs."""

    @staticmethod
    def get_client_info():
        """Get client IP and user agent from request."""
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:255] if request.headers.get('User-Agent') else None
        return ip_address, user_agent

    @staticmethod
    def get_current_user_info():
        """Get current user ID and username."""
        if current_user.is_authenticated:
            return current_user.id, current_user.username
        return None, 'Anonymous'

    @staticmethod
    def log_create(entity_type, entity_id, entity_name, details=None):
        """Log a CREATE operation."""
        from app.models.audit import AuditLog

        user_id, username = AuditService.get_current_user_info()
        ip_address, user_agent = AuditService.get_client_info()

        details_json = json.dumps(details) if details else None

        AuditLog.log(
            user_id=user_id,
            username=username,
            action='CREATE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_update(entity_type, entity_id, entity_name, changes=None):
        """Log an UPDATE operation."""
        from app.models.audit import AuditLog

        user_id, username = AuditService.get_current_user_info()
        ip_address, user_agent = AuditService.get_client_info()

        changes_json = json.dumps(changes) if changes else None

        AuditLog.log(
            user_id=user_id,
            username=username,
            action='UPDATE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=changes_json,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_delete(entity_type, entity_id, entity_name):
        """Log a DELETE operation."""
        from app.models.audit import AuditLog

        user_id, username = AuditService.get_current_user_info()
        ip_address, user_agent = AuditService.get_client_info()

        AuditLog.log(
            user_id=user_id,
            username=username,
            action='DELETE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_action(action, entity_type, entity_id=None, entity_name=None, details=None):
        """Log a generic action."""
        from app.models.audit import AuditLog

        user_id, username = AuditService.get_current_user_info()
        ip_address, user_agent = AuditService.get_client_info()

        details_json = json.dumps(details) if details else None

        AuditLog.log(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent
        )
