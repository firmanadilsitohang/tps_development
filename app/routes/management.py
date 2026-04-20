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
    this_year = 2026
    
    # 1. PIE CHART: Progress TPS KP 4 & 3
    kp4_count = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3_count = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    kp_total = kp4_count + kp3_count

    # 2. HORIZONTAL BAR: TPS Advance per Division
    adv_by_div = db.session.query(Division.name, func.count(Employee.id))\
        .join(Employee)\
        .filter(Employee.current_tps_level.ilike('%ADVANCE%'))\
        .group_by(Division.name).all()
    
    # Hover data for TPS Advance
    adv_employees = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).all()
    adv_details = {}
    for emp in adv_employees:
        div_name = emp.division.name if emp.division else "No Division"
        if div_name not in adv_details: adv_details[div_name] = []
        adv_details[div_name].append({
            'name': emp.name,
            'photo': emp.photo or 'default.png',
            'theme': emp.last_activity_theme or 'No Theme Activity'
        })

    # 3. BAR CHART: Jishuken Mapping per Department
    jishuken_by_dept = db.session.query(Department.name, func.count(Employee.id))\
        .join(Employee)\
        .filter(Employee.current_tps_level.ilike('%JISHUKEN%'))\
        .group_by(Department.name).all()

    # 4. PENSION PROJECTION (2026-2047)
    pension_forecast = {str(y): 0 for y in range(2026, 2048)}
    all_kp = Employee.query.filter(Employee.current_tps_level.op('regexp')('4|3')).all()
    for emp in all_kp:
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

    # 6. UTILIZATION: Theme vs No Theme
    has_theme = Employee.query.filter(Employee.last_activity_theme != None, Employee.last_activity_theme != "").count()
    no_theme = Employee.query.filter((Employee.last_activity_theme == None) | (Employee.last_activity_theme == "")).count()

    # 7. DEMOGRAPHICS (Productive vs Non-Productive)
    # Group by level and age group
    levels = ['KP 4', 'KP 3', 'ADVANCE']
    demo_data = {lvl: {'prod': 0, 'non': 0} for lvl in levels}
    
    all_emps = Employee.query.all()
    for emp in all_emps:
        lvl = None
        if emp.current_tps_level:
            if '4' in emp.current_tps_level: lvl = 'KP 4'
            elif '3' in emp.current_tps_level: lvl = 'KP 3'
            elif 'ADVANCE' in emp.current_tps_level.upper(): lvl = 'ADVANCE'
        
        if lvl and emp.birth_date:
            age = this_year - emp.birth_date.year
            if age < 50: demo_data[lvl]['prod'] += 1
            else: demo_data[lvl]['non'] += 1
        elif lvl: # Assume productive if no birth date for safety or omit
            demo_data[lvl]['prod'] += 1

    return render_template('management/dashboard.html',
        # Chart 1
        kp4_count=kp4_count, kp3_count=kp3_count, kp_total=kp_total,
        # Chart 2
        adv_div_labels=[d[0] for d in adv_by_div], adv_div_values=[d[1] for d in adv_by_div],
        adv_details=adv_details,
        # Chart 3
        dept_labels=[d[0] for d in jishuken_by_dept], dept_values=[d[1] for d in jishuken_by_dept],
        # Chart 4
        forecast_labels=list(pension_forecast.keys()), forecast_values=list(pension_forecast.values()),
        # Chart 5
        batch_labels=b_labels, batch_kp3=b_kp3, batch_kp4=b_kp4,
        # Chart 6
        util_labels=['With Theme', 'No Theme'], util_values=[has_theme, no_theme],
        # Chart 7
        demo_data=demo_data
    )


@management.route('/home')
@login_required
@management_required
def home():
    this_year = 2026
    
    # 1. PIE CHART: Progress TPS KP 4 & 3
    kp4_count = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3_count = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    kp_total = kp4_count + kp3_count

    # 2. HORIZONTAL BAR: TPS Advance per Division
    adv_by_div = db.session.query(Division.name, func.count(Employee.id))\
        .join(Employee)\
        .filter(Employee.current_tps_level.ilike('%ADVANCE%'))\
        .group_by(Division.name).all()
    
    # Hover data for TPS Advance
    adv_employees = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).all()
    adv_details = {}
    for emp in adv_employees:
        div_name = emp.division.name if emp.division else "No Division"
        if div_name not in adv_details: adv_details[div_name] = []
        adv_details[div_name].append({
            'name': emp.name,
            'photo': emp.photo or 'default.png',
            'theme': emp.last_activity_theme or 'No Theme Activity'
        })

    # 3. BAR CHART: Jishuken Mapping per Department
    jishuken_by_dept = db.session.query(Department.name, func.count(Employee.id))\
        .join(Employee)\
        .filter(Employee.current_tps_level.ilike('%JISHUKEN%'))\
        .group_by(Department.name).all()

    # 4. PENSION PROJECTION (2026-2047)
    pension_forecast = {str(y): 0 for y in range(2026, 2048)}
    all_kp = Employee.query.filter(Employee.current_tps_level.op('regexp')('4|3')).all()
    for emp in all_kp:
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

    # 6. UTILIZATION: Theme vs No Theme
    has_theme = Employee.query.filter(Employee.last_activity_theme != None, Employee.last_activity_theme != "").count()
    no_theme = Employee.query.filter((Employee.last_activity_theme == None) | (Employee.last_activity_theme == "")).count()

    # 7. DEMOGRAPHICS (Productive vs Non-Productive)
    # Group by level and age group
    levels = ['KP 4', 'KP 3', 'ADVANCE']
    demo_data = {lvl: {'prod': 0, 'non': 0} for lvl in levels}
    
    all_emps = Employee.query.all()
    for emp in all_emps:
        lvl = None
        if emp.current_tps_level:
            if '4' in emp.current_tps_level: lvl = 'KP 4'
            elif '3' in emp.current_tps_level: lvl = 'KP 3'
            elif 'ADVANCE' in emp.current_tps_level.upper(): lvl = 'ADVANCE'
        
        if lvl and emp.birth_date:
            age = this_year - emp.birth_date.year
            if age < 50: demo_data[lvl]['prod'] += 1
            else: demo_data[lvl]['non'] += 1
        elif lvl: # Assume productive if no birth date for safety or omit
            demo_data[lvl]['prod'] += 1

    return render_template('management/home.html',
        # Chart 1
        kp4_count=kp4_count, kp3_count=kp3_count, kp_total=kp_total,
        # Chart 2
        adv_div_labels=[d[0] for d in adv_by_div], adv_div_values=[d[1] for d in adv_by_div],
        adv_details=adv_details,
        # Chart 3
        dept_labels=[d[0] for d in jishuken_by_dept], dept_values=[d[1] for d in jishuken_by_dept],
        # Chart 4
        forecast_labels=list(pension_forecast.keys()), forecast_values=list(pension_forecast.values()),
        # Chart 5
        batch_labels=b_labels, batch_kp3=b_kp3, batch_kp4=b_kp4,
        # Chart 6
        util_labels=['With Theme', 'No Theme'], util_values=[has_theme, no_theme],
        # Chart 7
        demo_data=demo_data
    )