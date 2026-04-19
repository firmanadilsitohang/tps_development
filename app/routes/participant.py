import os
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from app import db
# Pastikan Division, Department, dan Plant di-import di sini
from app.models.employee import Employee, WorkshopActivity, Division, Department, Plant, WorkshopEvaluation
from app.models.module import LearningModule
from app.models.development import News, Training
from sqlalchemy import or_, desc

participant = Blueprint('participant', __name__, url_prefix='/participant')

# Daftar format file yang diizinkan untuk tugas
ALLOWED_EXTENSIONS = {'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@participant.route('/dashboard')
@login_required
def dashboard():
    # 1. Ambil data employee
    employee = Employee.query.options(
        joinedload(Employee.plant),
        joinedload(Employee.division),
        joinedload(Employee.department)
    ).filter_by(username=current_user.username).first()
    
    # --- HITUNG USIA DAN TAHUN PENSIUN ---
    umur = None
    tahun_pensiun = None
    if employee and employee.birth_date:
        today = date.today()
        # Kalkulasi umur akurat berdasarkan bulan dan hari
        umur = today.year - employee.birth_date.year - ((today.month, today.day) < (employee.birth_date.month, employee.birth_date.day))
        # Asumsi standar usia pensiun adalah 55 tahun
        tahun_pensiun = employee.birth_date.year + 55
    
    # 2. Ambil data untuk widget (Dikosongkan sementara sampai tabel Training dibuat)
    upcoming_trainings = [] 
    
    # 3. Ambil aktivitas yang sudah terhubung dengan WorkshopActivity baru
    my_activities = []
    if employee:
        my_activities = WorkshopActivity.query.filter_by(employee_id=employee.id).order_by(WorkshopActivity.submitted_at.desc()).limit(3).all()
    
    # 4. AMBIL PENGUMUMAN DAN JADWAL (Filter Berdasarkan Target)
    news_events = []
    if employee:
        user_nik = str(employee.username)
        news_events = News.query.filter(
            or_(
                News.target_type == 'all',
                News.target_users.like(f'%{user_nik}%')
            )
        ).order_by(News.created_at.desc()).limit(5).all()

    # 5. AMBIL JADWAL PELATIHAN (UPCOMING TRAININGS)
    upcoming_trainings = Training.query.order_by(Training.training_date.asc()).filter(Training.training_date >= datetime.now()).limit(5).all()

    # 6. AMBIL HASIL EVALUASI SPIDER CHART (OMDD)
    latest_eval = None
    show_evaluation = False
    if employee:
        latest_eval = WorkshopEvaluation.query.filter_by(employee_id=employee.id).order_by(WorkshopEvaluation.evaluated_at.desc()).first()
        
        # LOGIKA VISIBILITAS: Hanya muncul untuk ADVANCE, KP3, dan JISHUKEN
        lvl = str(employee.current_tps_level or '').upper()
        if 'ADVANCE' in lvl or 'KP 3' in lvl or 'KP3' in lvl or 'KEY PERSON 3' in lvl or 'JISHUKEN' in lvl:
            # Kecuali jika dia KP 4 (Kadang ada label ganda, kita prioritaskan sembunyikan jika sudah KP 4)
            if 'KP 4' not in lvl and 'KP4' not in lvl and 'KEY PERSON 4' not in lvl:
                show_evaluation = True
    
    # 7. AMBIL MODUL PEMBELAJARAN TERBARU
    recent_modules = LearningModule.query.order_by(LearningModule.created_at.desc()).limit(3).all()

    return render_template('participant/dashboard.html', 
                           employee=employee, 
                           trainings=upcoming_trainings, 
                           activities=my_activities,
                           news_events=news_events,
                           umur=umur,
                           tahun_pensiun=tahun_pensiun,
                           latest_eval=latest_eval,
                           show_evaluation=show_evaluation,
                           recent_modules=recent_modules)

@participant.route('/modules')
@login_required
def modules():
    semua_modul = LearningModule.query.order_by(LearningModule.created_at.desc()).all()
    return render_template('participant/modules.html', modules=semua_modul)

# =======================================================
# HALAMAN AKTIVITAS (UPLOAD TUGAS / THEME)
# =======================================================
@participant.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    employee = Employee.query.filter_by(username=current_user.username).first()
    
    if request.method == 'POST':
        if not employee:
            flash('Data profil Anda tidak ditemukan di sistem.', 'danger')
            return redirect(url_for('participant.activity'))

        theme_title = request.form.get('theme_title')
        file = request.files.get('participant_file')

        if not theme_title or not file or file.filename == '':
            flash('Judul tema dan file dokumen wajib diisi!', 'warning')
            return redirect(url_for('participant.activity'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{employee.username}_{timestamp}.{ext}"
            
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/activities')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, safe_filename)
            
            try:
                file.save(file_path)
                
                new_activity = WorkshopActivity(
                    employee_id=employee.id,
                    theme_title=theme_title,
                    participant_file=safe_filename,
                    status='pending'
                )
                db.session.add(new_activity)

                employee.last_activity_type = 'Theme Upload'
                employee.last_activity_theme = theme_title
                
                db.session.commit()
                flash('Tugas Kaizen/Workshop berhasil diunggah! Menunggu penilaian OMDD.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat menyimpan data: {str(e)}', 'danger')
        else:
            flash('Format file tidak didukung! Gunakan PDF, Excel, PPT, atau Word.', 'danger')
            
        return redirect(url_for('participant.activity'))

    user_activities = []
    if employee:
        user_activities = WorkshopActivity.query.filter_by(employee_id=employee.id).order_by(WorkshopActivity.submitted_at.desc()).all()
    
    return render_template('participant/activity.html', activities=user_activities)

# =======================================================
# HALAMAN DIREKTORI DENGAN FILTERING LENGKAP & SORTING BATCH
# =======================================================
@participant.route('/directory')
@login_required
def directory():
    all_employees = Employee.query.options(
        joinedload(Employee.plant),
        joinedload(Employee.division),
        joinedload(Employee.department)
    ).filter_by(status='active').order_by(Employee.batch.asc()).all()

    divisions = db.session.query(Division).all()
    departments = db.session.query(Department).all()
    
    tps_levels = db.session.query(Employee.current_tps_level).filter(
        Employee.current_tps_level.isnot(None), 
        Employee.current_tps_level != ''
    ).distinct().all()
    tps_levels = [level[0] for level in tps_levels]

    return render_template('participant/directory.html', 
                           candidates=all_employees,
                           divisions=divisions,
                           departments=departments,
                           tps_levels=tps_levels)

# =======================================================
# HALAMAN UPDATE PROFIL PARTISIPAN
# =======================================================
@participant.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    employee = Employee.query.filter_by(username=current_user.username).first()
    
    if employee:
        new_name = request.form.get('name')
        birth_date_str = request.form.get('birth_date')
        new_theme = request.form.get('last_activity_theme')

        try:
            if new_name:
                employee.name = new_name
            if new_theme:
                employee.last_activity_theme = new_theme
            
            if birth_date_str:
                employee.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()

            db.session.commit()
            flash('Data profil berhasil diperbarui!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan profil: {str(e)}', 'danger')

    return redirect(url_for('participant.dashboard'))