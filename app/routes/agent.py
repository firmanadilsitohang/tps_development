from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db
from app.models.stams import Project, Department, UserSTAMS
from datetime import datetime, timezone

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/dashboard')
@login_required
def dashboard():
    """Agent Dashboard with Spider Chart and Project tracking."""
    # Placeholder for Agent data
    from app.models.stams import WorkshopProgress, Project, UserSTAMS
    
    # Try to find STAMS user
    agent = UserSTAMS.query.filter_by(username=current_user.username).first()
    if not agent:
        flash("STAMS Profile not found. Please contact TPSG.", "warning")
        return redirect(url_for('tpsg.dashboard'))

    progress = WorkshopProgress.query.filter_by(user_id=agent.id).first()
    projects = Project.query.filter_by(agent_id=agent.id).order_by(Project.start_date.desc()).all()
    
    return render_template('agent/dashboard.html', 
                         agent=agent, 
                         progress=progress, 
                         projects=projects)
def start_project():
    """
    STEP 1: Start Project
    When an Agent creates a Project, set status to 'On Progress'.
    """
    try:
        data = request.get_json()
        new_project = Project(
            agent_id=data.get('agent_id'),
            title=data.get('title'),
            category_4m=data.get('category_4m'),
            target_date=datetime.strptime(data.get('target_date'), '%Y-%m-%d').date(),
            status='On Progress' # Set directly to On Progress
        )
        db.session.add(new_project)
        db.session.commit()
        return jsonify({'message': 'Project started', 'project_id': new_project.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agent_bp.route('/projects/monitor', methods=['GET'])
def monitor_overdue():
    """
    STEP 2: Monitor Overdue
    Utility that checks target_date vs current_date.
    """
    today = datetime.now(timezone.utc).date()
    # Find all 'On Progress' projects that are past their target date
    overdue_projects = Project.query.filter(
        Project.status == 'On Progress',
        Project.target_date < today
    ).all()
    
    results = []
    for p in overdue_projects:
        results.append({
            'id': p.id,
            'title': p.title,
            'target_date': p.target_date.isoformat(),
            'status': 'Overdue'
        })
    
    return jsonify({'overdue_count': len(results), 'projects': results}), 200

@agent_bp.route('/project/submit/<int:project_id>', methods=['POST'])
def submit_project_result(project_id):
    """
    STEP 3: Submit Result & Hoshin Accumulation
    a. Change Project status to 'Completed'.
    b. [TRANSACTION] Automatically ADD impact to Department's actuals.
    c. Commit with rollback safety.
    """
    try:
        data = request.get_json()
        reduce_time = int(data.get('reduce_time_sec', 0))
        reduce_cost = int(data.get('reduce_cost_rp', 0))

        # Atomic Transaction Block
        project = Project.query.get_or_404(project_id)
        
        if project.status == 'Completed':
            return jsonify({'error': 'Project already completed'}), 400

        # Link to Department
        agent = UserSTAMS.query.get(project.agent_id)
        if not agent or not agent.dept_id:
            return jsonify({'error': 'Agent or Department not found'}), 404
            
        department = Department.query.get(agent.dept_id)

        # Update Project Status and Results
        project.reduce_time_sec = reduce_time
        project.reduce_cost_rp = reduce_cost
        project.actual_end_date = datetime.now(timezone.utc).date()
        project.status = 'Completed'

        # Accumulation Logic (Hoshin Alignment)
        department.actual_time += reduce_time
        department.actual_cost += reduce_cost

        # Final Database Commit
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Impact accumulated to Hoshin target',
            'accumulated_time': department.actual_time,
            'accumulated_cost': department.actual_cost
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
