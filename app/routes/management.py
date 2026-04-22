from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.employee import Employee, Plant, Division, Department, BatchStat
from app.models.user import User 
from sqlalchemy import func, case
from datetime import datetime, date

management = Blueprint('management', __name__, url_prefix='/management')

def management_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'management':
            flash('Akses ditolak.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@management.route('/dashboard')
@login_required
@management_required
def dashboard():
    # Main Landing Page with 3 Icons
    return render_template('management/dashboard.html')

def get_demo_data(level_filters, this_year=2026):
    demo_data = {lvl: {
        'prod': 0, 'non': 0, 
        'prod_list': [], 'non_list': []
    } for lvl in level_filters}
    
    all_emps = Employee.query.all()
    for emp in all_emps:
        lvl_match = None
        if emp.current_tps_level:
            curr_lvl = emp.current_tps_level.upper()
            for f in level_filters:
                # Better matching: handle "KP" vs "KEY PERSON"
                f_search = f.upper()
                if "KP" in f_search:
                    alt_search = f_search.replace("KP", "KEY PERSON")
                else:
                    alt_search = f_search
                
                if f_search in curr_lvl or alt_search in curr_lvl:
                    lvl_match = f
                    break
        
        if lvl_match:
            p_data = {
                'id': emp.id,
                'name': emp.name,
                'photo': emp.photo or 'default.png',
                'theme': emp.last_activity_theme or 'No Theme Activity',
                'level': emp.current_tps_level
            }
            
            if emp.birth_date:
                age = this_year - emp.birth_date.year
                if age < 50: 
                    demo_data[lvl_match]['prod'] += 1
                    demo_data[lvl_match]['prod_list'].append(p_data)
                else: 
                    demo_data[lvl_match]['non'] += 1
                    demo_data[lvl_match]['non_list'].append(p_data)
            else:
                # Assume productive if no birth date for monitoring purposes
                demo_data[lvl_match]['prod'] += 1
                demo_data[lvl_match]['prod_list'].append(p_data)
                
    return demo_data

@management.route('/utilized_kp')
@login_required
@management_required
def utilized_kp():
    this_year = 2026
    # 1. PIE CHART: Progress TPS KP 4 & 3
    kp4_count = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3_count = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    kp_total = kp4_count + kp3_count

    # 2. DIVISION MAPPING (KP 4 & 3)
    div_results = db.session.query(
        Division.name,
        func.count(case((Employee.current_tps_level.ilike('%4%'), Employee.id))),
        func.count(case((Employee.current_tps_level.ilike('%3%'), Employee.id)))
    ).join(Employee, Division.id == Employee.division_id)\
    .group_by(Division.name).all()

    # 3. DEPARTMENT MAPPING (KP 4 & 3)
    dept_results = db.session.query(
        Department.name,
        func.count(case((Employee.current_tps_level.ilike('%4%'), Employee.id))),
        func.count(case((Employee.current_tps_level.ilike('%3%'), Employee.id)))
    ).join(Employee, Department.id == Employee.department_id)\
    .group_by(Department.name).all()

    # Tooltip details for mapping
    kp_participants = Employee.query.filter(Employee.current_tps_level.op('regexp')('3|4')).all()
    kp_div_details = {}
    kp_dept_details = {}
    
    for emp in kp_participants:
        p_data = {
            'name': emp.name,
            'level': 'KP 4' if '4' in emp.current_tps_level else 'KP 3',
            'photo': emp.photo or 'default.png',
            'theme': emp.last_activity_theme or 'No Theme Activity'
        }
        div_name = emp.division.name if emp.division else "No Division"
        if div_name not in kp_div_details: kp_div_details[div_name] = []
        kp_div_details[div_name].append(p_data)

        dept_name = emp.department.name if emp.department else "No Department"
        if dept_name not in kp_dept_details: kp_dept_details[dept_name] = []
        kp_dept_details[dept_name].append(p_data)

    # 4. PENSION PROJECTION (2026-2047)
    pension_forecast = {str(y): 0 for y in range(2026, 2048)}
    all_all_kp = Employee.query.filter(Employee.current_tps_level.op('regexp')('4|3')).all()
    for emp in all_all_kp:
        if emp.birth_date:
            p_year = emp.birth_date.year + 55
            if str(p_year) in pension_forecast:
                pension_forecast[str(p_year)] += 1

    # 5. PASSING RATE (Batch Stat)
    batch_stats = BatchStat.query.all()
    b_labels, b_kp3, b_kp4 = [], [], []
    for bs in batch_stats:
        b_labels.append(bs.batch_name)
        def parse_pct(val):
            v_str = str(val).replace('%', '').strip()
            try: return int(float(v_str))
            except: return 0
        b_kp3.append(parse_pct(bs.kp3_percent))
        b_kp4.append(parse_pct(bs.kp4_percent))

    demo_data = get_demo_data(['KP 4', 'KP 3'], this_year)

    return render_template('management/utilized_kp.html',
        kp4_count=kp4_count, kp3_count=kp3_count, kp_total=kp_total,
        kp_div_labels=[r[0] for r in div_results], kp_div_4=[r[1] for r in div_results], kp_div_3=[r[2] for r in div_results],
        kp_div_details=kp_div_details,
        kp_dept_labels=[r[0] for r in dept_results], kp_dept_4=[r[1] for r in dept_results], kp_dept_3=[r[2] for r in dept_results],
        kp_dept_details=kp_dept_details,
        forecast_labels=list(pension_forecast.keys()), forecast_values=list(pension_forecast.values()),
        batch_labels=b_labels, batch_kp3=b_kp3, batch_kp4=b_kp4,
        demo_data=demo_data
    )

@management.route('/tps_advance')
@login_required
@management_required
def tps_advance():
    this_year = 2026
    adv_by_div = db.session.query(Division.name, func.count(Employee.id))\
        .join(Employee).filter(Employee.current_tps_level.ilike('%ADVANCE%'))\
        .group_by(Division.name).all()
    
    adv_employees = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).all()
    adv_details = {}
    for emp in adv_employees:
        div_name = emp.division.name if emp.division else "No Division"
        if div_name not in adv_details: adv_details[div_name] = []
        adv_details[div_name].append({
            'name': emp.name, 'photo': emp.photo or 'default.png', 'theme': emp.last_activity_theme or 'No Theme Activity'
        })
    demo_data = get_demo_data(['ADVANCE'], this_year)
    return render_template('management/tps_advance.html',
        adv_div_labels=[d[0] for d in adv_by_div], adv_div_values=[d[1] for d in adv_by_div],
        adv_details=adv_details, demo_data=demo_data
    )

@management.route('/jishuken_office')
@login_required
@management_required
def jishuken_office():
    this_year = 2026
    jishuken_by_dept = db.session.query(Department.name, func.count(Employee.id))\
        .join(Employee).filter(Employee.current_tps_level.ilike('%JISHUKEN%'))\
        .group_by(Department.name).all()
    has_theme = Employee.query.filter(Employee.last_activity_theme != None, Employee.last_activity_theme != "").count()
    no_theme = Employee.query.filter((Employee.last_activity_theme == None) | (Employee.last_activity_theme == "")).count()
    demo_data = get_demo_data(['JISHUKEN'], this_year)
    return render_template('management/jishuken_office.html',
        dept_labels=[d[0] for d in jishuken_by_dept], dept_values=[d[1] for d in jishuken_by_dept],
        util_labels=['With Theme', 'No Theme'], util_values=[has_theme, no_theme],
        demo_data=demo_data
    )

@management.route('/participants')
@login_required
@management_required
def participants():
    employees = Employee.query.all()
    return render_template('management/participants.html', employees=employees)

@management.route('/participant_detail/<int:id>')
@login_required
@management_required
def participant_detail(id):
    emp = Employee.query.get_or_404(id)
    
    # Theme History
    themes = []
    for act in emp.workshop_activities:
        themes.append({
            'title': act.theme_title,
            'status': act.status,
            'score': act.score,
            'date': act.submitted_at.strftime('%Y-%m-%d') if act.submitted_at else '-'
        })
    
    # OMDD Assessment (WorkshopEvaluation) - specifically for KP 3
    assessment = None
    if emp.current_tps_level and '3' in emp.current_tps_level:
        eval = emp.workshop_evaluations[-1] if emp.workshop_evaluations else None
        if eval:
            assessment = {
                'genba': eval.score_genba,
                'ps': eval.score_problem_solving,
                'obs': eval.score_observasi,
                'kaizen': eval.score_kaizen,
                'impl': eval.score_implementation,
                'pres': eval.score_presentation,
                'decision': eval.final_decision,
                'notes': eval.notes
            }

    return {
        'id': emp.id,
        'name': emp.name,
        'username': emp.username,
        'position': emp.position or '-',
        'department': emp.department.name if emp.department else '-',
        'division': emp.division.name if emp.division else '-',
        'plant': emp.plant.name if emp.plant else '-',
        'photo': emp.photo or 'default.png',
        'level': emp.current_tps_level,
        'themes': themes,
        'assessment': assessment
    }

@management.route('/home')
@login_required
@management_required
def home():
    return redirect(url_for('management.dashboard'))