"""
Audit Log Routes - Viewer for CRUD audit trail.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.audit import AuditLog
from app import db
from functools import wraps

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


def tpsg_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['tpsg', 'admin']:
            flash('Akses ditolak.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@audit_bp.route('/logs')
@login_required
@tpsg_required
def logs():
    page = request.args.get('page', 1, type=int)
    per_page = 50

    action_filter = request.args.get('action')
    entity_filter = request.args.get('entity')
    search = request.args.get('search', '').strip()

    query = AuditLog.query

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    if entity_filter:
        query = query.filter(AuditLog.entity_type == entity_filter)

    if search:
        query = query.filter(
            (AuditLog.username.ilike(f'%{search}%')) |
            (AuditLog.entity_name.ilike(f'%{search}%')) |
            (AuditLog.ip_address.ilike(f'%{search}%'))
        )

    query = query.order_by(AuditLog.timestamp.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    return render_template('audit/logs.html',
                           logs=logs,
                           pagination=pagination,
                           page=page,
                           action_filter=action_filter,
                           entity_filter=entity_filter,
                           search=search)


@audit_bp.route('/logs/export')
@login_required
@tpsg_required
def export_logs():
    from flask import make_response
    import csv
    from io import StringIO

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(1000).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID', 'Entity Name', 'IP Address', 'User Agent'])

    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.username or 'Anonymous',
            log.action,
            log.entity_type,
            log.entity_id or '',
            log.entity_name or '',
            log.ip_address or '',
            log.user_agent or ''
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=audit_logs.csv'

    return response


@audit_bp.route('/stats')
@login_required
@tpsg_required
def stats():
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)

    total = AuditLog.query.count()
    week_count = AuditLog.query.filter(AuditLog.timestamp >= week_ago).count()

    action_counts = db.session.query(
        AuditLog.action, func.count(AuditLog.id)
    ).group_by(AuditLog.action).all()

    entity_counts = db.session.query(
        AuditLog.entity_type, func.count(AuditLog.id)
    ).group_by(AuditLog.entity_type).order_by(func.count(AuditLog.id).desc()).all()

    recent_users = db.session.query(
        AuditLog.username, func.count(AuditLog.id)
    ).filter(AuditLog.username != 'Anonymous').group_by(
        AuditLog.username
    ).order_by(func.count(AuditLog.id).desc()).limit(10).all()

    return render_template('audit/stats.html',
                           total=total,
                           week_count=week_count,
                           action_counts=action_counts,
                           entity_counts=entity_counts,
                           recent_users=recent_users)


@audit_bp.route('/logs/cleanup', methods=['POST'])
@login_required
@tpsg_required
def cleanup_logs():
    """Delete audit logs older than specified days."""
    from datetime import datetime, timedelta, timezone

    days = request.form.get('days', type=int)
    if not days or days < 1:
        flash('Invalid cleanup period.', 'danger')
        return redirect(url_for('audit.logs'))

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
    db.session.commit()

    flash(f'{deleted} log(s) older than {days} days deleted.', 'success')
    return redirect(url_for('audit.logs'))
