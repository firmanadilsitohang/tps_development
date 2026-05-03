from flask import Blueprint, jsonify
from app.models import db
from app.models.stams import WorkshopProgress, Department, Project, UserSTAMS, Section
from sqlalchemy import func

api_bp = Blueprint('api', __name__, url_prefix='/api/data')

@api_bp.route('/spider-chart/<int:user_id>', methods=['GET'])
def get_spider_chart(user_id):
    """Returns 7 workshop scores for Radar Chart."""
    progress = WorkshopProgress.query.filter_by(user_id=user_id).first()
    if not progress:
        return jsonify({'error': 'No data found'}), 404
    
    return jsonify({
        'labels': ['WS 1', 'WS 2', 'WS 3', 'WS 4', 'WS 5', 'WS 6', 'WS 7'],
        'scores': [progress.ws_1, progress.ws_2, progress.ws_3, progress.ws_4, progress.ws_5, progress.ws_6, progress.ws_7]
    })

@api_bp.route('/hoshin-alignment', methods=['GET'])
def get_hoshin_alignment():
    """Returns target vs actual for Time and Cost by Department."""
    depts = Department.query.all()
    labels = [d.name for d in depts]
    target_time = [d.target_time for d in depts]
    actual_time = [d.actual_time for d in depts]
    target_cost = [d.target_cost for d in depts]
    actual_cost = [d.actual_cost for d in depts]

    return jsonify({
        'labels': labels,
        'time_data': {'target': target_time, 'actual': actual_time},
        'cost_data': {'target': target_cost, 'actual': actual_cost}
    })

@api_bp.route('/section-radar', methods=['GET'])
def get_section_radar():
    """Returns agent counts grouped by Section and Project Status."""
    # Logic: Get sections, count projects per status in each section
    sections = Section.query.all()
    results = []
    
    for section in sections:
        # Count statuses for projects of agents in this section
        counts = db.session.query(
            Project.status, func.count(Project.id)
        ).join(UserSTAMS, Project.agent_id == UserSTAMS.id)\
         .filter(UserSTAMS.section_id == section.id)\
         .group_by(Project.status).all()
        
        status_map = dict(counts)
        results.append({
            'section': section.name,
            'idle': status_map.get('Idle', 0),
            'on_progress': status_map.get('On Progress', 0),
            'completed': status_map.get('Completed', 0),
            'overdue': status_map.get('Overdue', 0)
        })

    return jsonify(results)

@api_bp.route('/project-tracking', methods=['GET'])
def get_project_tracking():
    """Returns project timelines for Gantt Chart."""
    projects = Project.query.all()
    data = []
    for p in projects:
        data.append({
            'id': p.id,
            'title': p.title,
            'start': p.start_date.isoformat(),
            'end': p.target_date.isoformat(),
            'status': p.status
        })
    return jsonify(data)
