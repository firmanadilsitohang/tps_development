"""
Custom decorators for role-based access control.
"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Decorator that requires user to have one of the specified roles.
    Usage: @role_required('bod', 'management')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Silakan login terlebih dahulu.', 'warning')
                return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                flash('Anda tidak memiliki akses ke halaman ini.', 'danger')
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def bod_required(f):
    """Decorator that requires BOD (Board of Directors) role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))

        if current_user.role not in ['bod', 'admin', 'tpsg', 'management']:
            flash('Akses ditolak. Halaman ini khusus untuk Direksi.', 'danger')
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function


def division_head_required(f):
    """Decorator that requires Division Head role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))

        if current_user.role not in ['division_head', 'admin', 'tpsg', 'management']:
            flash('Akses ditolak. Halaman ini khusus untuk Kepala Divisi.', 'danger')
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function


def any_manager_required(f):
    """Decorator that requires any management-level role (bod, management, division_head)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login'))

        if current_user.role not in ['bod', 'management', 'division_head', 'admin', 'tpsg']:
            flash('Akses ditolak. Halaman ini khusus untuk Management.', 'danger')
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function
