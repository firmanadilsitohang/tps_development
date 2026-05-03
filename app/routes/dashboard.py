from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.stams import Department, Project, Section, UserSTAMS
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/management')
@login_required
def management():
    """Management Dashboard (Dept Head / BOD)"""
    # Check if user is Dept Head or BOD
    # (In a real app, use @role_required('Dept Head', 'BOD', 'TPSG'))
    
    departments = Department.query.all()
    total_target_cost = sum(d.target_cost for d in departments)
    total_actual_cost = sum(d.actual_cost for d in departments)
    
    cost_performance = (total_actual_cost / total_target_cost * 100) if total_target_cost > 0 else 0
    
    return render_template('dashboard/management.html', 
                         departments=departments,
                         total_target_cost=total_target_cost,
                         total_actual_cost=total_actual_cost,
                         cost_performance=cost_performance)
