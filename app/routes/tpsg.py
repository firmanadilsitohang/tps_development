import os
import pandas as pd
import random
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash
from app import db
from app.models.user import User
from app.models.employee import Employee, Department, Plant, Division, WorkshopActivity
from sqlalchemy.orm import joinedload
from datetime import datetime, date
from sqlalchemy import func

tpsg = Blueprint('tpsg', __name__, url_prefix='/tpsg')

def tpsg_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'tpsg':
            flash('Akses ditolak.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# =======================================================
# 1. DASHBOARD ANALYTICS (FIXED & STABLE)
# =======================================================
@tpsg.route('/dashboard')
@login_required
@tpsg_required
def dashboard():
    # Counter Utama
    total = Employee.query.count() or 0
    active = Employee.query.filter_by(status='active').count() or 0
    
    # Ambil ID yang sudah lulus (status approved)
    graduated_query = db.session.query(WorkshopActivity.employee_id).filter_by(status='approved').all()
    graduated_ids = {item[0] for item in graduated_query}

    # --- GRAFIK 1: ACHIEVEMENT LEVEL PROFILE ---
    target_levels = ['TPS KEY PERSON 4', 'TPS KEY PERSON 3', 'TPS ADVANCE']
    level_stats = db.session.query(Employee.current_tps_level, func.count(Employee.id))\
        .filter(Employee.current_tps_level.in_(target_levels))\
        .group_by(Employee.current_tps_level).all()
    lv_map = {item[0]: item[1] for item in level_stats}
    kp_values = [lv_map.get(lvl, 0) for lvl in target_levels]

    # --- GRAFIK 2: TREN KELULUSAN TPS KP 4 ---
    kp4_stats = db.session.query(Employee.tahun_lulus_saat_ini, func.count(Employee.id))\
        .filter(Employee.current_tps_level == 'TPS KEY PERSON 4')\
        .filter(Employee.tahun_lulus_saat_ini != None)\
        .group_by(Employee.tahun_lulus_saat_ini)\
        .order_by(Employee.tahun_lulus_saat_ini.asc()).all()
    
    kp4_year_labels = [str(i[0]) for i in kp4_stats] if kp4_stats else ["No Data"]
    kp4_year_values = [int(i[1]) for i in kp4_stats] if kp4_stats else [0]

    # --- GRAFIK 3: DISTRIBUTION BY DIVISION ---
    div_stats = db.session.query(Division.name, func.count(Employee.id))\
        .select_from(Employee).outerjoin(Division)\
        .group_by(Division.name).all()
    div_labels = [str(i[0]) if i[0] else 'Other' for i in div_stats] if div_stats else ["No Data"]
    div_values = [int(i[1]) for i in div_stats] if div_stats else [0]

    # --- GRAFIK 4: DISTRIBUTION BY DEPARTMENT ---
    dept_stats = db.session.query(Department.name, func.count(Employee.id))\
        .select_from(Employee).outerjoin(Department)\
        .group_by(Department.name).limit(10).all()
    dept_labels = [str(i[0]) if i[0] else 'Other' for i in dept_stats] if dept_stats else ["No Data"]
    dept_values = [int(i[1]) for i in dept_stats] if dept_stats else [0]

    # --- GRAFIK 5: BATCH SUCCESS RATE ---
    all_emps = Employee.query.all()
    batch_map = {}
    for emp in all_emps:
        b = emp.batch or "No Batch"
        if b not in batch_map: batch_map[b] = {'t': 0, 'g': 0}
        batch_map[b]['t'] += 1
        if emp.id in graduated_ids: batch_map[b]['g'] += 1
    
    sorted_b = sorted(batch_map.items())
    batch_labels = [i[0] for i in sorted_b] if sorted_b else ["-"]
    batch_rates = [round((i[1]['g']/i[1]['t']*100), 1) if i[1]['t'] > 0 else 0 for i in sorted_b] if sorted_b else [0]

    # --- GRAFIK 6: AGE PROFILE ---
    a_u50, a_o50, c_year = 0, 0, date.today().year
    for emp in all_emps:
        if emp.birth_date:
            age = c_year - emp.birth_date.year
            if age >= 50: a_o50 += 1
            else: a_u50 += 1
        else: a_u50 += 1 # Default ke produktif

    return render_template('tpsg/dashboard.html',
        total=total, active=active, pending=0,
        kp_labels=target_levels, kp_values=kp_values,
        kp4_year_labels=kp4_year_labels, kp4_year_values=kp4_year_values,
        div_labels=div_labels, div_values=div_values,
        dept_labels=dept_labels, dept_values=dept_values,
        batch_labels=batch_labels, batch_rates=batch_rates,
        age_labels=['Produktif (<50)', 'Risiko Pensiun (>=50)'], age_values=[a_u50, a_o50])

# =======================================================
# 2. IMPORT SYSTEM (SECURE IMPORT)
# =======================================================
@tpsg.route('/import-excel', methods=['GET', 'POST'])
@login_required
@tpsg_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Pilih file Excel atau CSV.', 'warning')
            return redirect(url_for('tpsg.import_excel'))
        
        try:
            dfs = {}
            if file.filename.endswith('.csv'):
                dfs = {'Data': pd.read_csv(file)}
            else:
                dfs = pd.read_excel(file, sheet_name=None)
            
            for sn, df in dfs.items():
                if df is None: continue
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                for _, row in df.iterrows():
                    noreg = str(row.get('NOREG', row.get('NPK', ''))).strip()
                    if noreg == 'nan' or not noreg: continue
                    
                    raw_name = str(row.get('NAMA', '')).strip()
                    valid_name = raw_name if (raw_name and raw_name != 'nan') else f"User {noreg}"

                    emp = Employee.query.filter_by(username=noreg).first()
                    if not emp:
                        emp = Employee(username=noreg, name=valid_name, status='active')
                        db.session.add(emp); db.session.flush()
                        u = User(username=noreg, role='participant', employee_id=emp.id, 
                                 password=generate_password_hash('tmmin123'))
                        db.session.add(u)
                    else:
                        emp.name = valid_name

                    emp.batch = str(row.get('BATCH', 'No Batch')).strip()
                    kp = str(row.get('KP_ID', '')).upper()
                    if 'KP 4' in kp: emp.current_tps_level = 'TPS KEY PERSON 4'
                    elif 'KP 3' in kp: emp.current_tps_level = 'TPS KEY PERSON 3'
                    elif 'ADVANCE' in kp: emp.current_tps_level = 'TPS ADVANCE'
                    
                    thn = row.get('TAHUN LULUS')
                    if pd.notna(thn):
                        try: emp.tahun_lulus_saat_ini = str(int(float(thn)))
                        except: pass
            
            db.session.commit()
            flash('Import Berhasil! Data Dashboard telah diperbarui.', 'success')
            return redirect(url_for('tpsg.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal Import: {str(e)}', 'danger')
            
    return render_template('tpsg/import_excel.html')

# =======================================================
# 3. OTHER ROUTES
# =======================================================
@tpsg.route('/employees')
@login_required
@tpsg_required
def employees():
    all_participants = Employee.query.filter_by(status='active').all()
    return render_template('tpsg/employees.html', employees=all_participants)

@tpsg.route('/manage-news')
@login_required
@tpsg_required
def manage_news():
    return render_template('tpsg/manage_news.html')

@tpsg.route('/generate-dummy')
@login_required
@tpsg_required
def generate_dummy():
    try:
        for i in range(50):
            npk = f"940{random.randint(1000, 9999)}"
            if Employee.query.filter_by(username=npk).first(): continue
            emp = Employee(
                name=f"Employee {i}", 
                username=npk, 
                batch=f"#{random.randint(1,11)}",
                current_tps_level=random.choice(['TPS KEY PERSON 4', 'TPS KEY PERSON 3', 'TPS ADVANCE']),
                tahun_lulus_saat_ini=str(random.randint(2022, 2026)),
                status='active'
            )
            db.session.add(emp); db.session.flush()
            if random.random() > 0.5:
                work = WorkshopActivity(employee_id=emp.id, theme_title="Kaizen Project", status='approved')
                db.session.add(work)
        db.session.commit()
        flash('Data Dummy Berhasil Dibuat!', 'success')
        return redirect(url_for('tpsg.dashboard'))
    except Exception as e:
        db.session.rollback()
        return f"Error: {str(e)}"