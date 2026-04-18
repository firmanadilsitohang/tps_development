import os
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.employee import Employee, Plant, Division, Department, BatchStat
from app.models.user import User 
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, case, text
from datetime import datetime, date

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
# 1. DASHBOARD COMMAND CENTER
# =======================================================
@tpsg.route('/dashboard')
@login_required
@tpsg_required
def dashboard():
    this_year = 2026
    kp4 = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3 = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    adv = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).count()
    
    plant_stats = db.session.query(Plant.name, func.count(Employee.id)).join(Employee).group_by(Plant.name).all()
    div_stats = db.session.query(Division.name, func.count(Employee.id)).join(Employee).group_by(Division.name).all()
    # PERBAIKAN: Menambahkan kembali query Departemen yang terhapus
    dept_stats = db.session.query(Department.name, func.count(Employee.id)).join(Employee).group_by(Department.name).order_by(func.count(Employee.id).desc()).limit(10).all()
    
    emps = Employee.query.all()
    prod, risk = 0, 0
    pension_forecast = {str(y): 0 for y in range(2026, 2031)}
    
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

    batch_stats = BatchStat.query.all()
    if batch_stats:
        b_labels = []
        b_kp3 = []
        b_kp4 = []
        for bs in batch_stats:
            b_labels.append(bs.batch_name)
            def parse_pct(val):
                v_str = str(val).replace('%', '').strip()
                if not v_str or v_str.lower() == 'nan': return 0
                try:
                    vf = float(v_str)
                    if vf <= 1.0 and '%' not in str(val):
                        return int(vf * 100)
                    return int(vf)
                except:
                    return 0
            b_kp3.append(parse_pct(bs.kp3_percent))
            b_kp4.append(parse_pct(bs.kp4_percent))
        
        r_batch_labels = b_labels
        r_batch_kp3 = b_kp3
        r_batch_kp4 = b_kp4
    else:
        r_batch_labels = ['B-01', 'B-11']
        r_batch_kp3 = [5, 95]
        r_batch_kp4 = [15, 0]

    return render_template('tpsg/dashboard.html', 
        kp_labels=['TPS KP 4', 'TPS KP 3', 'TPS ADVANCE'], kp_values=[kp4, kp3, adv],
        plant_labels=[p[0] for p in plant_stats], plant_values=[p[1] for p in plant_stats],
        div_labels=[d[0] for d in div_stats], div_values=[d[1] for d in div_stats],
        # PERBAIKAN: Mengirimkan data Departemen dan Batch ke HTML agar tidak error Undefined
        dept_labels=[dt[0] for dt in dept_stats], dept_values=[dt[1] for dt in dept_stats],
        forecast_labels=list(pension_forecast.keys()), forecast_values=list(pension_forecast.values()),
        age_labels=['Produktif (<50)', 'Risk Area (>=50)'], age_values=[prod, risk],
        batch_labels=r_batch_labels, batch_kp3=r_batch_kp3, batch_kp4=r_batch_kp4
    )

# =======================================================
# 2. DIRECTORY PARTISIPAN
# =======================================================
@tpsg.route('/employees')
@login_required
@tpsg_required
def employees():
    all_participants = Employee.query.order_by(Employee.name.asc()).all()
    return render_template('tpsg/employees.html', employees=all_participants)

# =======================================================
# 3. IMPORT EXCEL (SMART COLUMN MAPPING)
# =======================================================
@tpsg.route('/import-excel', methods=['GET', 'POST'])
@login_required
@tpsg_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Pilih file dulu!', 'warning')
            return redirect(request.url)
        try:
            excel_file = pd.ExcelFile(file)
            
            # Cek format file khusus Batch Success Rate
            is_batch_stats = False
            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)
                cols_check = [str(c).strip().upper() for c in df.columns]
                
                if "BATCH" in cols_check and "PARTICIPAN" in cols_check and "KP 3" in cols_check:
                    is_batch_stats = True
                    df.columns = cols_check
                    
                    BatchStat.query.delete()
                    
                    def safe_int(val):
                        try:
                            if pd.notnull(val): return int(float(val))
                        except: pass
                        return 0

                    for _, row in df.iterrows():
                        b_val = str(row['BATCH']).strip()
                        if b_val.upper() in ['TOTAL', 'NAN', 'N/A', '']:
                            continue
                            
                        stat = BatchStat(
                            batch_name=b_val,
                            participant_count=safe_int(row.get('PARTICIPAN')),
                            kp3_count=safe_int(row.get('KP 3')),
                            kp4_count=safe_int(row.get('KP 4')),
                            kp3_percent=str(row.get('%KP3', '')),
                            kp4_percent=str(row.get('%KP4', ''))
                        )
                        db.session.add(stat)
                        
                    db.session.commit()
                    break

            if is_batch_stats:
                flash('Import Sukses! Grafik Batch Success Rate telah diperbarui.', 'success')
                return redirect(url_for('tpsg.dashboard'))

            def process_sheet(sheet_name, default_level_func):
                if sheet_name in excel_file.sheet_names:
                    df = excel_file.parse(sheet_name)
                    df.columns = [str(c).strip().upper() for c in df.columns]
                    
                    for _, row in df.iterrows():
                        # Pencarian Kolom NIK/NOREG
                        noreg = None
                        for col in ['NOREG', 'NIK', 'NO REG']:
                            if col in row:
                                noreg = str(row[col]).replace('.0', '').strip()
                                break
                        
                        if not noreg or noreg.lower() == 'nan': continue
                        if len(noreg) == 7: noreg = "0" + noreg
                        
                        # Pencarian Nama
                        nama = "Tanpa Nama"
                        for col in ['NAMA', 'NAME', 'NAMA LENGKAP']:
                            if col in row and pd.notnull(row[col]):
                                nama = str(row[col]).strip()
                                break

                        emp = Employee.query.filter_by(username=noreg).first()
                        if not emp:
                            emp = Employee(username=noreg, name=nama)
                            db.session.add(emp)
                            db.session.flush() 
                        else:
                            emp.name = nama

                        # Pencarian Tahun Lahir
                        birth_year = None
                        for col in ['TAHUN LAHIR', 'THN LAHIR', 'BIRTH YEAR', 'YEAR']:
                            if col in row and pd.notnull(row[col]):
                                try:
                                    birth_year = int(float(row[col]))
                                    break
                                except: pass
                        
                        if birth_year:
                            emp.birth_date = date(birth_year, 1, 1)

                        emp.position = str(row.get('JABATAN', emp.position))
                        emp.photo = str(row.get('FOTO', emp.photo))
                        
                        # --- Area / Plant ---
                        plant_name = None
                        if 'PLANT_ID' in row and pd.notnull(row['PLANT_ID']):
                            plant_name = str(row['PLANT_ID']).strip()
                        if plant_name:
                            p = Plant.query.filter_by(name=plant_name).first()
                            if not p:
                                p = Plant(name=plant_name); db.session.add(p); db.session.flush()
                            emp.plant_id = p.id
                            
                        # --- Division ---
                        div_name = None
                        if 'DIVISI' in row and pd.notnull(row['DIVISI']):
                            div_name = str(row['DIVISI']).strip()
                        if div_name:
                            div = Division.query.filter_by(name=div_name).first()
                            if not div:
                                div = Division(name=div_name); db.session.add(div); db.session.flush()
                            emp.division_id = div.id
                            
                        # --- Department ---
                        dept_name = None
                        if 'DEPARTEMEN' in row and pd.notnull(row['DEPARTEMEN']):
                            dept_name = str(row['DEPARTEMEN']).strip()
                        if dept_name:
                            dept = Department.query.filter_by(name=dept_name).first()
                            if not dept:
                                dept = Department(name=dept_name); db.session.add(dept); db.session.flush()
                            emp.department_id = dept.id
                        
                        new_level = default_level_func(row)
                        if emp.current_tps_level:
                            if new_level not in emp.current_tps_level:
                                emp.current_tps_level += f", {new_level}"
                        else:
                            emp.current_tps_level = new_level

                        if not User.query.filter_by(employee_id=emp.id).first():
                            db.session.add(User(username=noreg, password=generate_password_hash('tmmin123'), role='participant', employee_id=emp.id))

            process_sheet('TPS KP', lambda r: "KEY PERSON 4" if "4" in str(r.get('KP_ID', '')) else "KEY PERSON 3")
            process_sheet('TPS ADVANCE', lambda r: "ADVANCE")
            process_sheet('MEMBER OFFICE JISHUKEN', lambda r: "JISHUKEN MEMBER")

            db.session.commit()
            flash('Import Sukses! Data & Grafik telah diperbarui.', 'success')
            return redirect(url_for('tpsg.employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('tpsg/import_excel.html')

# =======================================================
# 4. HAPUS & RESET DATA 
# =======================================================
@tpsg.route('/bulk-delete-employees', methods=['POST'])
@login_required
@tpsg_required
def bulk_delete_employees():
    ids = request.form.getlist('employee_ids')
    if ids:
        try:
            safe_ids = [str(int(i)) for i in ids]
            ids_string = ",".join(safe_ids)
            db.session.execute(text(f"DELETE FROM users WHERE employee_id IN ({ids_string})"))
            Employee.query.filter(Employee.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            flash(f'{len(ids)} data partisipan berhasil dihapus permanen.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Gagal menghapus data: Terjadi kesalahan sistem.', 'danger')
    return redirect(url_for('tpsg.employees'))

@tpsg.route('/reset-all-employees', methods=['POST'])
@login_required
@tpsg_required
def reset_all_employees():
    try:
        db.session.execute(text("DELETE FROM users WHERE employee_id IS NOT NULL"))
        db.session.query(Employee).delete()
        db.session.commit()
        flash('Berhasil! Seluruh data partisipan lama beserta akun terkait telah dikosongkan.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mengosongkan data: {str(e)}', 'danger')
    return redirect(url_for('tpsg.import_excel'))

# =======================================================
# 5. RUTE DETAIL EMPLOYEE (FITUR UPDATE)
# =======================================================
@tpsg.route('/employee/<int:id>', methods=['GET', 'POST'])
@login_required
@tpsg_required
def detail_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        employee.name = request.form.get('name')
        new_username = request.form.get('username')
        if new_username and new_username != employee.username:
            employee.username = new_username
            if employee.user:
                employee.user.username = new_username
                
        birth_date_str = request.form.get('birth_date')
        if birth_date_str:
            employee.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            
        employee.position = request.form.get('position')
        
        plant_name = request.form.get('plant')
        if plant_name:
            p = Plant.query.filter_by(name=plant_name).first()
            if not p:
                p = Plant(name=plant_name); db.session.add(p); db.session.flush()
            employee.plant_id = p.id
            
        div_name = request.form.get('division')
        if div_name:
            div = Division.query.filter_by(name=div_name).first()
            if not div:
                div = Division(name=div_name); db.session.add(div); db.session.flush()
            employee.division_id = div.id
            
        dept_name = request.form.get('department')
        if dept_name:
            dept = Department.query.filter_by(name=dept_name).first()
            if not dept:
                dept = Department(name=dept_name); db.session.add(dept); db.session.flush()
            employee.department_id = dept.id
            
        password = request.form.get('password')
        if password and employee.user:
            employee.user.password = generate_password_hash(password)
            
        employee.previous_tps_level = request.form.get('previous_tps_level')
        employee.tahun_lulus_terakhir = request.form.get('tahun_lulus_terakhir')
        employee.current_tps_level = request.form.get('current_tps_level')
        employee.tahun_lulus_saat_ini = request.form.get('tahun_lulus_saat_ini')
        employee.last_activity_type = request.form.get('last_activity_type')
        employee.last_activity_theme = request.form.get('last_activity_theme')
        employee.batch = request.form.get('batch')
        
        photo = request.files.get('photo')
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            upload_folder = os.path.join(os.getcwd(), 'app', 'static', 'uploads', 'photos')
            os.makedirs(upload_folder, exist_ok=True)
            photo.save(os.path.join(upload_folder, filename))
            employee.photo = filename
            
        certificate = request.files.get('certificate')
        if certificate and certificate.filename != '':
            filename = secure_filename(certificate.filename)
            upload_folder = os.path.join(os.getcwd(), 'app', 'static', 'uploads', 'certificates')
            os.makedirs(upload_folder, exist_ok=True)
            certificate.save(os.path.join(upload_folder, filename))
            employee.certificate = filename
            
        try:
            db.session.commit()
            flash('Data partisipan berhasil diperbarui!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            
        return redirect(url_for('tpsg.detail_employee', id=id))

    return render_template('tpsg/detail_employee.html', employee=employee, emp=employee)

# =======================================================
# 6. RUTE LAINNYA (MANAGE NEWS & DUMMY)
# =======================================================
@tpsg.route('/manage-news')
@login_required
@tpsg_required
def manage_news(): 
    return render_template('tpsg/manage_news.html')

@tpsg.route('/generate-dummy')
@login_required
@tpsg_required
def generate_dummy(): 
    return redirect(url_for('tpsg.dashboard'))