from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.models.employee import Employee, Plant, Division, Department, BatchStat, WorkshopEvaluation
from app.models.development import Activity
from app.models.module import LearningModule 
from werkzeug.utils import secure_filename
from app import db
from sqlalchemy import func
from datetime import date, datetime
import os

omdd = Blueprint('omdd', __name__, url_prefix='/omdd')

@omdd.route('/dashboard')
@login_required
def dashboard():
    # Proteksi: Jika bukan OMDD, lempar ke login
    if current_user.role != 'omdd':
        return redirect(url_for('auth.login'))

    # 1. DATA RINGKASAN UNTUK DASHBOARD OMDD
    stats = {
        'total_karyawan': Employee.query.count(),
        'total_kaizen': Activity.query.count(),
        'pending_review': Activity.query.filter_by(status='pending').count(),
        'total_kp4': Employee.query.filter(
            func.upper(Employee.current_tps_level).contains('PERSON 4')
        ).count()
    }

    # 2. DATA UNTUK GRAFIK DISTRIBUSI LEVEL (Doughnut Chart)
    level_counts = db.session.query(Employee.current_tps_level, func.count(Employee.id)).group_by(Employee.current_tps_level).all()
    level_labels = [str(item[0]) if item[0] else 'Unassigned' for item in level_counts]
    level_data = [int(item[1]) for item in level_counts]

    # 3. DATA UNTUK GRAFIK PER PLANT (Bar Chart)
    plant_counts = db.session.query(Plant.name, func.count(Employee.id)).select_from(Employee).outerjoin(Plant).group_by(Plant.name).all()
    plant_labels = [str(item[0]) if item[0] else 'Belum Ada Plant' for item in plant_counts]
    plant_data = [int(item[1]) for item in plant_counts]

    # 4. DATA UNTUK GRAFIK PER DIVISI (Bar Chart)
    div_counts = db.session.query(Division.name, func.count(Employee.id)).select_from(Employee).outerjoin(Division).group_by(Division.name).all()
    div_labels = [str(item[0]) if item[0] else 'Tanpa Divisi' for item in div_counts]
    div_data = [int(item[1]) for item in div_counts]

    # 5. DATA UNTUK GRAFIK PER DEPARTEMEN (Bar Chart) — Top 10
    dept_counts = db.session.query(Department.name, func.count(Employee.id)).select_from(Employee).outerjoin(Department).group_by(Department.name).order_by(func.count(Employee.id).desc()).limit(10).all()
    dept_labels = [str(item[0]) if item[0] else 'Tanpa Departemen' for item in dept_counts]
    dept_data = [int(item[1]) for item in dept_counts]

    # 6. DATA UNTUK GRAFIK STATUS KAIZEN (Pie Chart)
    status_counts = db.session.query(Activity.status, func.count(Activity.id)).group_by(Activity.status).all()
    status_labels = [str(item[0]).upper() for item in status_counts]
    status_data = [int(item[1]) for item in status_counts]

    # 7. DATA UNTUK GRAFIK TREN KELULUSAN (Line Chart)
    completed_activities = Activity.query.filter_by(status='Completed').all()
    trend_dict = {}
    for act in completed_activities:
        if act.updated_at:
            month_key = act.updated_at.strftime('%Y-%m')
            trend_dict[month_key] = trend_dict.get(month_key, 0) + 1
    sorted_trend = sorted(trend_dict.items())
    trend_labels = [item[0] for item in sorted_trend] if sorted_trend else ["No Data"]
    trend_values = [item[1] for item in sorted_trend] if sorted_trend else [0]

    # ============================================================
    # TPSG-STYLE CHART DATA (BARU: Pension, Age, KP Level, Batch)
    # ============================================================
    this_year = date.today().year
    kp4 = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3 = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    adv = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).count()

    emps = Employee.query.all()
    prod, risk = 0, 0
    pension_forecast = {str(y): 0 for y in range(this_year, this_year + 5)}
    for e in emps:
        if e.birth_date:
            age = this_year - e.birth_date.year
            if age >= 50: risk += 1
            else: prod += 1
            p_year = e.birth_date.year + 55
            if str(p_year) in pension_forecast:
                pension_forecast[str(p_year)] += 1
        else:
            prod += 1

    # Data Batch Success Rate
    batch_stats = BatchStat.query.all()
    if batch_stats:
        b_labels, b_kp3, b_kp4 = [], [], []
        for bs in batch_stats:
            b_labels.append(bs.batch_name)
            def parse_pct(val):
                v_str = str(val).replace('%', '').strip()
                if not v_str or v_str.lower() == 'nan': return 0
                try:
                    vf = float(v_str)
                    return int(vf * 100) if vf <= 1.0 and '%' not in str(val) else int(vf)
                except: return 0
            b_kp3.append(parse_pct(bs.kp3_percent))
            b_kp4.append(parse_pct(bs.kp4_percent))
    else:
        b_labels = ['B-01', 'B-11']
        b_kp3 = [5, 95]
        b_kp4 = [15, 0]

    # 8. DATA TABEL MONITORING DAN SIDE PANEL KARYAWAN
    all_employees = Employee.query.order_by(Employee.name.asc()).all()

    def get_join_year(emp):
        nik_str = str(emp.username).strip()
        if nik_str.isdigit():
            nik_str = nik_str.zfill(8)
        if len(nik_str) >= 3:
            prefix = nik_str[:3] 
            if prefix[0] == '0' and prefix[1:].isdigit():
                yy = int(prefix[1:]) 
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
            elif prefix[:2].isdigit(): 
                yy = int(prefix[:2])
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
        return (9999, nik_str) 

    all_employees_sorted = sorted(all_employees, key=get_join_year)

    # 9. DATA TUGAS YANG MENUNGGU DINILAI (PENDING ACTIVITIES)
    pending_activities = Activity.query.filter_by(status='pending').order_by(Activity.submitted_at.asc()).all()

    # 10. DATA EVALUASI WORKSHOP (untuk panel spider chart)
    # Buat dict: employee_id -> evaluasi terakhir
    all_evals = WorkshopEvaluation.query.all()
    eval_map = {ev.employee_id: ev for ev in all_evals}

    return render_template('omdd/dashboard.html', 
                           stats=stats, 
                           level_labels=level_labels, level_data=level_data,
                           plant_labels=plant_labels, plant_data=plant_data,
                           div_labels=div_labels, div_data=div_data,
                           dept_labels=dept_labels, dept_data=dept_data,
                           status_labels=status_labels, status_data=status_data,
                           trend_labels=trend_labels, trend_values=trend_values,
                           employees=all_employees_sorted,
                           pending_activities=pending_activities,
                           # Data TPSG-style charts
                           kp_labels=['TPS KP 4', 'TPS KP 3', 'TPS ADVANCE'],
                           kp_values=[kp4, kp3, adv],
                           forecast_labels=list(pension_forecast.keys()),
                           forecast_values=list(pension_forecast.values()),
                           age_labels=['Produktif (<50)', 'Risk Area (>=50)'],
                           age_values=[prod, risk],
                           batch_labels=b_labels, batch_kp3=b_kp3, batch_kp4=b_kp4,
                           # Data evaluasi workshop
                           eval_map=eval_map)

# ==========================================
# FITUR EVALUASI TUGAS / ACTIVITY
# ==========================================
@omdd.route('/evaluate-activity/<int:activity_id>', methods=['POST'])
@login_required
def evaluate_activity(activity_id):
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    activity = Activity.query.get_or_404(activity_id)
    
    score = request.form.get('score')
    status = request.form.get('status')
    feedback = request.form.get('feedback')

    try:
        if score:
            activity.score = int(score)
        if status:
            activity.status = status
        if feedback:
            activity.feedback = feedback

        db.session.commit()
        flash(f'Tugas "{activity.theme_title}" milik {activity.employee.name} berhasil dinilai!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menyimpan nilai: {str(e)}', 'danger')

    return redirect(url_for('omdd.dashboard'))

@omdd.route('/view-log/<int:emp_id>')
@login_required
def view_log(emp_id):
    if current_user.role != 'omdd':
        return redirect(url_for('auth.login'))

    employee = db.session.get(Employee, emp_id)
    if not employee:
        return "Employee tidak ditemukan", 404

    activities = Activity.query.filter_by(employee_id=emp_id).order_by(Activity.id.desc()).all()

    return render_template('omdd/view_log.html', 
                           employee=employee, 
                           activities=activities)

# ==========================================
# PENILAIAN LEVEL KARYAWAN (ASSESSMENT)
# ==========================================
@omdd.route('/assess/<int:id>', methods=['GET', 'POST'])
@login_required
def assess_employee(id):
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    employee = Employee.query.get_or_404(id)

    if request.method == 'POST':
        new_level = request.form.get('current_tps_level')

        if employee.current_tps_level != new_level:
            employee.previous_tps_level = employee.current_tps_level
            
        employee.current_tps_level = new_level
        employee.tahun_lulus_saat_ini = request.form.get('tahun_lulus_saat_ini')
        employee.last_activity_type = request.form.get('last_activity_type')
        employee.last_activity_theme = request.form.get('last_activity_theme')

        try:
            db.session.commit()
            flash(f'Data level untuk {employee.name} berhasil diperbarui!', 'success')
            return redirect(url_for('omdd.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan data: {str(e)}', 'danger')

    return render_template('omdd/assess.html', employee=employee)

@omdd.route('/detail/<int:id>')
@login_required
def detail_employee(id):
    if current_user.role != 'omdd':
        return redirect(url_for('auth.login'))

    employee = Employee.query.get_or_404(id)

    umur = 0
    if employee.birth_date:
        today = date.today()
        umur = today.year - employee.birth_date.year - ((today.month, today.day) < (employee.birth_date.month, employee.birth_date.day))

    return render_template('omdd/detail.html', employee=employee, umur=umur)

# ==========================================
# ==========================================
# HALAMAN PARTISIPAN (TABEL LENGKAP)
# ==========================================
@omdd.route('/participants')
@login_required
def participants():
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    all_employees = Employee.query.order_by(Employee.name.asc()).all()

    def get_join_year(emp):
        nik_str = str(emp.username).strip()
        if nik_str.isdigit():
            nik_str = nik_str.zfill(8)
        if len(nik_str) >= 3:
            prefix = nik_str[:3]
            if prefix[0] == '0' and prefix[1:].isdigit():
                yy = int(prefix[1:])
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
            elif prefix[:2].isdigit():
                yy = int(prefix[:2])
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
        return (9999, nik_str)

    all_employees_sorted = sorted(all_employees, key=get_join_year)

    all_evals = WorkshopEvaluation.query.all()
    eval_map = {ev.employee_id: ev for ev in all_evals}

    return render_template('omdd/participants.html',
                           employees=all_employees_sorted,
                           eval_map=eval_map)

# MASTER DIRECTORY (DAFTAR SEMUA KARYAWAN)
# ==========================================
@omdd.route('/directory')
@login_required
def directory():
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    all_employees = Employee.query.all()

    def get_join_year(emp):
        nik_str = str(emp.username).strip()
        if nik_str.isdigit():
            nik_str = nik_str.zfill(8)
            
        if len(nik_str) >= 3:
            prefix = nik_str[:3]
            if prefix[0] == '0' and prefix[1:].isdigit():
                yy = int(prefix[1:])
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
            elif prefix[:2].isdigit():
                yy = int(prefix[:2])
                year = 1900 + yy if yy > 50 else 2000 + yy
                return (year, nik_str)
                
        return (9999, nik_str)

    all_employees_sorted = sorted(all_employees, key=get_join_year)

    return render_template('omdd/directory.html', employees=all_employees_sorted)

# ==========================================
# MANAJEMEN MODUL (E-LEARNING) - KHUSUS OMDD
# ==========================================
@omdd.route('/manage-modules', methods=['GET', 'POST'])
@login_required
def manage_modules():
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        tps_level = request.form.get('tps_level')
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('Gagal: Tidak ada file dokumen/video yang dipilih.', 'danger')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/modules')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            new_module = LearningModule(
                title=title, description=description, tps_level=tps_level, file_name=filename
            )
            db.session.add(new_module)
            
            try:
                db.session.commit()
                flash('Modul berhasil diunggah dan disimpan ke sistem!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Terjadi kesalahan saat menyimpan data ke database.', 'danger')
                
            return redirect(url_for('omdd.manage_modules'))

    modules = LearningModule.query.order_by(LearningModule.created_at.desc()).all()
    return render_template('omdd/manage_modules.html', modules=modules)

# ==========================================
# EVALUASI WORKSHOP (SPIDER CHART OMDD)
# ==========================================
@omdd.route('/evaluate-workshop/<int:emp_id>', methods=['POST'])
@login_required
def submit_workshop_evaluation(emp_id):
    if current_user.role != 'omdd':
        flash('Akses ditolak. Halaman khusus OMDD.', 'danger')
        return redirect(url_for('auth.login'))

    employee = Employee.query.get_or_404(emp_id)

    # Ambil atau buat evaluasi baru
    evaluation = WorkshopEvaluation.query.filter_by(employee_id=emp_id).first()
    if not evaluation:
        evaluation = WorkshopEvaluation(employee_id=emp_id)
        db.session.add(evaluation)

    try:
        evaluation.score_genba = int(request.form.get('score_genba', 0))
        evaluation.score_problem_solving = int(request.form.get('score_problem_solving', 0))
        evaluation.score_observasi = int(request.form.get('score_observasi', 0))
        evaluation.score_kaizen = int(request.form.get('score_kaizen', 0))
        evaluation.score_implementation = int(request.form.get('score_implementation', 0))
        evaluation.score_presentation = int(request.form.get('score_presentation', 0))
        evaluation.final_decision = request.form.get('final_decision', 'PASS')
        evaluation.notes = request.form.get('notes', '')
        evaluation.evaluated_by = current_user.username
        evaluation.evaluated_at = datetime.utcnow()

        db.session.commit()
        flash(f'Evaluasi Workshop untuk {employee.name} berhasil disimpan!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('omdd.detail_employee', id=emp_id))

