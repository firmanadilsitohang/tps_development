import os
import pandas as pd
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.employee import Employee, Plant, Division, Department, BatchStat, WorkshopEvaluation
from app.models.module import LearningModule
from app.models.user import User
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, text
from datetime import datetime, date, timezone

tpsg = Blueprint('tpsg', __name__, url_prefix='/tpsg')

def tpsg_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
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
    this_year = date.today().year
    from sqlalchemy import case

    # TPS Level Counts
    kp4 = Employee.query.filter(Employee.current_tps_level.ilike('%4%')).count()
    kp3 = Employee.query.filter(Employee.current_tps_level.ilike('%3%')).count()
    adv = Employee.query.filter(Employee.current_tps_level.ilike('%ADVANCE%')).count()
    jishuken = Employee.query.filter(Employee.current_tps_level.ilike('%JISHUKEN%')).count()

    # Organization Stats
    plant_stats = db.session.query(Plant.name, func.count(Employee.id)).join(Employee).group_by(Plant.name).all()
    div_stats = db.session.query(Division.name, func.count(Employee.id)).join(Employee).group_by(Division.name).all()
    dept_stats = db.session.query(Department.name, func.count(Employee.id)).join(Employee).group_by(Department.name).order_by(func.count(Employee.id).desc()).limit(12).all()

    # Age Analysis (build pension_forecast AND count prod/risk in one pass)
    emps = Employee.query.all()
    prod, risk = 0, 0
    pension_forecast = {str(y): 0 for y in range(2026, 2048)}
    proj_years = [str(y) for y in range(2026, 2031)]

    # Chart 7: Age breakdown for KP3 and KP4 participants (reuse emps loop)
    kp3_under50 = kp3_over50 = kp4_under50 = kp4_over50 = 0

    for e in emps:
        if e.birth_date:
            age = this_year - e.birth_date.year
            if age >= 50: risk += 1
            else: prod += 1

            p_year = e.birth_date.year + 55
            if str(p_year) in pension_forecast:
                pension_forecast[str(p_year)] += 1

            # Age + Level breakdown for Chart 7
            lvl = (e.current_tps_level or '').upper()
            if '4' in lvl:
                if age < 50: kp4_under50 += 1
                else: kp4_over50 += 1
            elif '3' in lvl:
                if age < 50: kp3_under50 += 1
                else: kp3_over50 += 1
        else:
            prod += 1

    # Chart 6: Projection 2026-2030
    # Fixed data based on user description:
    # - 2026: start with 15 KP4
    # - Each year people retire: 2, 5, 7, 2, 10 (2026-2030)
    # - Target: grow to 60 KP4 by 2030 (linear ramp from 15 → 60)
    proj_years = ['2026', '2027', '2028', '2029', '2030']
    proj_retiring   = [2, 5, 7, 2, 10]   # yearly retirees
    proj_target60   = [27, 36, 43, 55, 60]  # target ramp to 60 by 2030
    proj_actual_kp4 = [15, 13,  8,  1,  0]  # 15 - cumulative retirees
    proj_recommend  = [14, 14, 14, 14, 15]  # recommended workshop passes per year

    # Build retiring employee data per year for tooltip
    retiring_by_year = {y: [] for y in proj_years}
    for e in emps:
        if e.birth_date:
            r_year = str(e.birth_date.year + 55)
            if r_year in retiring_by_year:
                retiring_by_year[r_year].append({
                    'id': e.id,
                    'name': e.name,
                    'position': e.position or '-',
                    'photo': e.photo or '',
                    'username': e.username,
                    'current_tps_level': e.current_tps_level or '-'
                })

    # Build KP3 candidates per year for tooltip (for recommended pass bars)
    kp3_candidates = [e for e in emps if e.current_tps_level and '3' in e.current_tps_level.upper() and not ('4' in e.current_tps_level.upper())]
    recommend_by_year = {}
    for i, yr in enumerate(proj_years):
        count = proj_recommend[i]
        # Get candidates not yet in KP4, up to 'count'
        candidates = []
        for e in kp3_candidates:
            if len(candidates) >= count:
                break
            candidates.append({
                'id': e.id,
                'name': e.name,
                'position': e.position or '-',
                'photo': e.photo or '',
                'username': e.username,
                'current_tps_level': e.current_tps_level or '-'
            })
        # Fill with dummy names if not enough candidates
        for j in range(max(0, count - len(candidates))):
            candidates.append({
                'id': f'demo_{i}_{j}',
                'name': f'Kandidat {j+1}',
                'position': 'KP 3 Candidate',
                'photo': '',
                'username': f'NP-00{j+1}',
                'current_tps_level': 'KP 3'
            })
        recommend_by_year[yr] = candidates

    proj_participants = {
        'retiring': {yr: retiring_by_year[yr] for yr in proj_years},
        'recommend': recommend_by_year
    }

    # ── Build participant data for all chart tooltips ──
    def emp_to_dict(e):
        """Serialize employee for JS tooltip"""
        latest = None
        if e.workshop_activities:
            latest = max(e.workshop_activities, key=lambda a: a.submitted_at or datetime.min)
        theme = e.last_activity_theme or (latest.theme_title if latest else '-')
        activity_type = e.last_activity_type or (latest.status if latest else '-')
        return {
            'id': e.id,
            'name': e.name,
            'position': e.position or '-',
            'photo': e.photo or '',
            'username': e.username,
            'current_tps_level': e.current_tps_level or '-',
            'theme': theme,
            'activity_type': activity_type,
            'plant': e.plant.name if e.plant else '-',
            'division': e.division.name if e.division else '-',
            'department': e.department.name if e.department else '-'
        }

    # Chart 1: TPS Level Pie
    kp4_emps = [emp_to_dict(e) for e in Employee.query.filter(Employee.current_tps_level.ilike('%4%')).all()]
    kp3_emps = [emp_to_dict(e) for e in Employee.query.filter(Employee.current_tps_level.ilike('%3%')).filter(~Employee.current_tps_level.ilike('%4%')).all()]

    # Chart 2: Plant / Area breakdown
    plant_emp_results = db.session.query(
        Plant.name,
        func.count(Employee.id)
    ).join(Employee).group_by(Plant.name).all()
    plant_emp_data = {}
    for p_name, _ in plant_emp_results:
        emps = Employee.query.join(Plant).filter(Plant.name == p_name).all()
        plant_emp_data[p_name] = [emp_to_dict(e) for e in emps]

    # Chart 3: Division breakdown
    div_emp_results = db.session.query(
        Division.name,
        func.count(Employee.id)
    ).join(Employee).group_by(Division.name).all()
    div_emp_data = {}
    for d_name, _ in div_emp_results:
        emps = Employee.query.join(Division).filter(Division.name == d_name).all()
        div_emp_data[d_name] = [emp_to_dict(e) for e in emps]

    # Chart 4: Department breakdown
    dept_emp_results = db.session.query(
        Department.name,
        func.count(Employee.id)
    ).join(Employee).group_by(Department.name).all()
    dept_emp_data = {}
    for dt_name, _ in dept_emp_results:
        emps = Employee.query.join(Department).filter(Department.name == dt_name).all()
        dept_emp_data[dt_name] = [emp_to_dict(e) for e in emps]

    # Chart 5: Batch breakdown
    batch_emp_data = {}

    chart_participants = {
        'pie': {'KP4': kp4_emps, 'KP3': kp3_emps},
        'plant': plant_emp_data,
        'division': div_emp_data,
        'department': dept_emp_data,
        'batch': batch_emp_data
    }

    # Batch Stats
    batch_stats = BatchStat.query.all()
    r_batch_labels = ['B-01', 'B-11']
    r_batch_kp3 = [5, 95]
    r_batch_kp4 = [15, 0]
    if batch_stats:
        import re as _re
        batch_stats_sorted = sorted(batch_stats, key=lambda bs: int(_re.search(r'\d+', str(bs.batch_name)).group()) if _re.search(r'\d+', str(bs.batch_name)) else 0)
        r_batch_labels = [bs.batch_name for bs in batch_stats_sorted]

        def parse_pct(val):
            v_str = str(val).replace('%', '').strip()
            if not v_str or v_str.lower() == 'nan': return 0
            try:
                vf = float(v_str)
                return int(vf * 100) if vf <= 1.0 and '%' not in str(val) else int(vf)
            except: return 0

        r_batch_kp3 = [parse_pct(bs.kp3_percent) for bs in batch_stats_sorted]
        r_batch_kp4 = [parse_pct(bs.kp4_percent) for bs in batch_stats_sorted]

    # Division breakdown by KP level
    kp_div_results = db.session.query(
        Division.name,
        func.count(case((Employee.current_tps_level.ilike('%4%'), Employee.id))),
        func.count(case((Employee.current_tps_level.ilike('%3%'), Employee.id)))
    ).join(Employee, Division.id == Employee.division_id)\
     .group_by(Division.name).all()

    # Department breakdown by TPS level
    dept_level_results = db.session.query(
        Department.name, func.count(Employee.id)
    ).join(Employee).group_by(Department.name).all()

    # Operational Metrics
    pending_count = Employee.query.filter_by(status='pending').count()
    incomplete_count = Employee.query.filter(
        (Employee.photo == None) | (Employee.photo == '') |
        (Employee.certificate == None) | (Employee.certificate == '')
    ).count()
    total_count = Employee.query.count()
    data_health = int(((total_count - incomplete_count) / total_count * 100)) if total_count > 0 else 0

    return render_template('tpsg/dashboard.html',
        kp_values=[kp4, kp3, adv, jishuken],  # KPI cards + projection stats
        # Chart 1: Pie — TPS KP 4 vs KP 3 only
        pie_labels=['TPS KP 4', 'TPS KP 3'],
        pie_values=[kp4, kp3],
        plant_labels=[p[0] for p in plant_stats], plant_values=[p[1] for p in plant_stats],
        div_labels=[d[0] for d in div_stats], div_values=[d[1] for d in div_stats],
        dept_labels=[dt[0] for dt in dept_stats], dept_values=[dt[1] for dt in dept_stats],
        kp_div_labels=[r[0] for r in kp_div_results],
        kp_div_4=[r[1] for r in kp_div_results],
        kp_div_3=[r[2] for r in kp_div_results],
        forecast_labels=proj_years, forecast_values=proj_retiring,
        proj_labels=proj_years,
        proj_data=[{
            'labels': proj_years,
            'retiring': proj_retiring,
            'target60': proj_target60,
            'remaining': proj_actual_kp4,
            'recommend': proj_recommend
        }],
        proj_participants=proj_participants,
        chart_participants=chart_participants,
        age_labels=['Produktif (<50)', 'Risk Area (>=50)'], age_values=[prod, risk],
        batch_labels=r_batch_labels, batch_kp3=r_batch_kp3, batch_kp4=r_batch_kp4,
        kp3_under50=kp3_under50, kp3_over50=kp3_over50,
        kp4_under50=kp4_under50, kp4_over50=kp4_over50,
        pending_count=pending_count,
        incomplete_count=incomplete_count,
        total_count=total_count,
        data_health=data_health
    )

# =======================================================
# 2. DIRECTORY PARTISIPAN
# =======================================================
@tpsg.route('/employees')
@login_required
@tpsg_required
def employees():
    """Main Participant Directory using the modern STAMS layout."""
    from app.services.employee_service import EmployeeService
    status_filter = request.args.get('status')
    all_participants = EmployeeService.get_all_employees(status_filter)
    return render_template('tpsg/participant_list.html', employees=all_participants)

# =======================================================
# 3. IMPORT EXCEL (SMART COLUMN MAPPING) - REFACTORED
# =======================================================
import pandas as pd
from datetime import date
from flask import request, flash, redirect, url_for, render_template
from werkzeug.security import generate_password_hash
# Asumsi import model database (db, Employee, User, Plant, Division, Department, BatchStat) sudah ada di bagian atas file.

@tpsg.route('/import-excel', methods=['GET', 'POST'])
@login_required
@tpsg_required
def import_excel():
    if request.method != 'POST':
        return render_template('tpsg/import_excel.html')

    file = request.files.get('file')
    if not file:
        flash('Pilih file dulu!', 'warning')
        return redirect(request.url)

    try:
        excel_file = pd.ExcelFile(file)
        is_batch_stats = False
        
        # --- 1. PRE-CACHING UNTUK OPTIMASI PERFORMA ---
        # Memuat data master ke memori (dictionary) untuk mencegah N+1 Query (query berulang di dalam loop)
        plants_cache = {p.name: p for p in Plant.query.all()}
        divs_cache = {d.name: d for d in Division.query.all()}
        depts_cache = {d.name: d for d in Department.query.all()}
        
        # --- 2. CEK & PROSES BATCH STATS ---
        for sheet_name in excel_file.sheet_names:
            # Baca header-nya saja dulu untuk mendeteksi jenis sheet
            df_header = excel_file.parse(sheet_name, nrows=0)
            cols_raw = [str(c).strip() for c in df_header.columns]
            cols_upper = [c.upper() for c in cols_raw]
            
            # Deteksi: Sheet harus punya kolom "BATCH" dan salah satu dari "KP 3", "KP 4", atau "PARTICIPAN"
            is_stats_sheet = any("BATCH" in c for c in cols_upper) and \
                             (any("KP 3" in c for c in cols_upper) or any("KP 4" in c for c in cols_upper))

            if is_stats_sheet:
                is_batch_stats = True
                df = excel_file.parse(sheet_name, dtype=str)
                df.columns = cols_upper
                
                BatchStat.query.delete()
                
                def safe_int(val):
                    try:
                        if pd.notnull(val) and str(val).strip().lower() != 'nan': 
                            return int(float(val))
                    except: pass
                    return 0

                def get_col_val(row, keywords):
                    """Mencari nilai kolom berdasarkan kumpulan keyword"""
                    for c in row.index:
                        if any(k.upper() in str(c).upper() for k in keywords):
                            return row[c]
                    return ''

                for _, row in df.iterrows():
                    b_val = get_col_val(row, ['BATCH'])
                    if not b_val or str(b_val).strip().upper() in ['TOTAL', 'NAN', 'N/A', 'NONE', '']:
                        continue
                        
                    stat = BatchStat(
                        batch_name=str(b_val).strip(),
                        participant_count=safe_int(get_col_val(row, ['PARTICIPAN', 'PESERTA', 'TOTAL'])),
                        kp3_count=safe_int(get_col_val(row, ['KP 3', 'KP3'])),
                        kp4_count=safe_int(get_col_val(row, ['KP 4', 'KP4'])),
                        kp3_percent=str(get_col_val(row, ['%KP3', '% KP 3', 'PERCENTAGE KP 3', 'PASSING RATE KP 3'])).replace('nan', '').strip(),
                        kp4_percent=str(get_col_val(row, ['%KP4', '% KP 4', 'PERCENTAGE KP 4', 'PASSING RATE KP 4'])).replace('nan', '').strip()
                    )
                    db.session.add(stat)
                
                db.session.commit()
                break # Keluar dari loop, statistik batch selesai

        if is_batch_stats:
            flash('Import Sukses! Grafik Batch Success Rate telah diperbarui.', 'success')
            return redirect(url_for('tpsg.dashboard'))

        # --- 3. PROSES MASTER DATA EMPLOYEE ---
        def process_sheet(sheet_name, default_level_func):
            if sheet_name not in excel_file.sheet_names:
                return

            # PENTING: dtype=str mencegah Pandas menghilangkan angka 0 di depan Noreg
            df = excel_file.parse(sheet_name, dtype=str)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            for _, row in df.iterrows():
                # Pencarian Noreg yang Aman
                noreg = None
                for col in ['NOREG', 'NIK', 'NO REG']:
                    if col in row and pd.notnull(row[col]):
                        val = str(row[col]).replace('.0', '').strip()
                        if val.lower() != 'nan' and val != '':
                            # Otomatis menambahkan '0' di depan hingga panjangnya genap 8 digit
                            noreg = val.zfill(8) 
                            break
                
                if not noreg: 
                    continue
                
                # Pencarian Nama
                nama = "Tanpa Nama"
                for col in ['NAMA', 'NAME', 'NAMA LENGKAP']:
                    if col in row and pd.notnull(row[col]):
                        val = str(row[col]).strip()
                        if val.lower() != 'nan' and val != '':
                            nama = val
                            break

                # Upsert Karyawan
                emp = Employee.query.filter_by(username=noreg).first()
                if not emp:
                    emp = Employee(username=noreg, name=nama, status='active')
                    db.session.add(emp)
                    db.session.flush() 
                else:
                    emp.name = nama

                # Parsing Tahun Lahir
                for col in ['TAHUN LAHIR', 'THN LAHIR', 'BIRTH YEAR', 'YEAR']:
                    if col in row and pd.notnull(row[col]):
                        val = str(row[col]).strip()
                        if val.lower() != 'nan' and val != '':
                            try:
                                emp.birth_date = date(int(float(val)), 1, 1)
                                break
                            except ValueError:
                                pass

                # Jabatan & Foto
                jabatan = str(row.get('JABATAN', '')).strip()
                foto = str(row.get('FOTO', '')).strip()
                if jabatan and jabatan.lower() != 'nan': emp.position = jabatan
                if foto and foto.lower() != 'nan': emp.photo = foto
                
                # Relasi Plant (Memanfaatkan Cache)
                plant_name = str(row.get('PLANT_ID', '')).strip()
                if plant_name and plant_name.lower() != 'nan':
                    if plant_name not in plants_cache:
                        p = Plant(name=plant_name)
                        db.session.add(p)
                        db.session.flush()
                        plants_cache[plant_name] = p
                    emp.plant_id = plants_cache[plant_name].id
                    
                # Relasi Division (Memanfaatkan Cache)
                div_name = str(row.get('DIVISI', '')).strip()
                if div_name and div_name.lower() != 'nan':
                    if div_name not in divs_cache:
                        div = Division(name=div_name)
                        db.session.add(div)
                        db.session.flush()
                        divs_cache[div_name] = div
                    emp.division_id = divs_cache[div_name].id
                    
                # Relasi Department (Memanfaatkan Cache)
                dept_name = str(row.get('DEPARTEMEN', '')).strip()
                if dept_name and dept_name.lower() != 'nan':
                    if dept_name not in depts_cache:
                        dept = Department(name=dept_name)
                        db.session.add(dept)
                        db.session.flush()
                        depts_cache[dept_name] = dept
                    emp.department_id = depts_cache[dept_name].id
                
                # Set Role/Level Dinamis
                new_level = default_level_func(row)
                if emp.current_tps_level:
                    if new_level not in emp.current_tps_level:
                        emp.current_tps_level += f", {new_level}"
                else:
                    emp.current_tps_level = new_level

                # Pembuatan User Login
                if not User.query.filter_by(employee_id=emp.id).first():
                    import_password = os.getenv('IMPORT_DEFAULT_PASSWORD', 'ChangeMe123!')
                    db.session.add(User(
                        username=noreg,
                        password=generate_password_hash(import_password),
                        role='participant',
                        employee_id=emp.id
                    ))

        # Panggil fungsi untuk memproses sheet-sheet yang relevan
        process_sheet('TPS KP', lambda r: "KEY PERSON 4" if "4" in str(r.get('KP_ID', '')) else "KEY PERSON 3")
        process_sheet('TPS ADVANCE', lambda r: "ADVANCE")
        process_sheet('MEMBER OFFICE JISHUKEN', lambda r: "JISHUKEN MEMBER")

        db.session.commit()
        flash('Import Sukses! Data & Grafik telah diperbarui.', 'success')
        return redirect(url_for('tpsg.employees'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(request.url)

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
            User.query.filter(User.employee_id.in_(safe_ids)).delete(synchronize_session=False)
            Employee.query.filter(Employee.id.in_(safe_ids)).delete(synchronize_session=False)
            db.session.commit()
            from app.services.audit_service import AuditService
            AuditService.log_delete('Employee', None, f'{len(ids)} employees', {'deleted_ids': safe_ids})
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
        from app.services.audit_service import AuditService
        AuditService.log_action('RESET', 'Employee', details={'action': 'reset_all_employees'})
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
    
    umur = 0
    if employee.birth_date:
        today = date.today()
        umur = today.year - employee.birth_date.year - ((today.month, today.day) < (employee.birth_date.month, employee.birth_date.day))

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

    return render_template('tpsg/detail_employee.html', employee=employee, emp=employee, umur=umur)

# ==========================================
# EVALUASI WORKSHOP (SPIDER CHART TPSG)
# ==========================================
@tpsg.route('/evaluate-workshop/<int:emp_id>', methods=['POST'])
@login_required
@tpsg_required
def submit_workshop_evaluation(emp_id):
    employee = Employee.query.get_or_404(emp_id)

    # Ambil atau buat evaluasi baru
    evaluation = WorkshopEvaluation.query.filter_by(employee_id=emp_id).first()
    if not evaluation:
        evaluation = WorkshopEvaluation(employee_id=emp_id)
        db.session.add(evaluation)

    try:
        evaluation.ws_1 = int(request.form.get('score_genba', 0))
        evaluation.ws_2 = int(request.form.get('score_problem_solving', 0))
        evaluation.ws_3 = int(request.form.get('score_observasi', 0))
        evaluation.ws_4 = int(request.form.get('score_kaizen', 0))
        evaluation.ws_5 = int(request.form.get('score_implementation', 0))
        evaluation.ws_6 = int(request.form.get('score_presentation', 0))
        evaluation.ws_7 = int(request.form.get('score_skillgap', 0))
        evaluation.final_decision = request.form.get('final_decision', 'PASS')
        evaluation.notes = request.form.get('notes', '')
        evaluation.evaluated_by = current_user.username
        evaluation.evaluated_at = datetime.now(timezone.utc)

        db.session.commit()
        flash(f'Evaluasi Workshop untuk {employee.name} berhasil disimpan!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan: {str(e)}', 'danger')

    return redirect(url_for('tpsg.detail_employee', id=emp_id))

# =======================================================
# 6. RUTE LAINNYA (MANAGE NEWS & DUMMY)
# =======================================================
# =======================================================
# 6. BROADCAST CENTER (NEWS & ANNOUNCEMENTS)
# =======================================================
@tpsg.route('/manage-news', methods=['GET', 'POST'])
@login_required
@tpsg_required
def manage_news():
    from app.forms.news_form import NewsForm
    from app.services.news_service import NewsService

    form = NewsForm()

    if request.method == 'POST' and form.validate_on_submit():
        data = {
            'title': form.title.data,
            'category': form.category.data,
            'content': form.content.data,
            'target_type': request.form.get('target_type', 'all'),
            'target_users': request.form.getlist('target_users')
        }
        success, _, message = NewsService.create_news(data)
        if success:
            from app.services.audit_service import AuditService
            AuditService.log_create('News', None, data['title'], {'category': data['category'], 'target_type': data['target_type']})
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('tpsg.manage_news'))

    all_news = NewsService.get_all_news()
    employees = Employee.query.order_by(Employee.name.asc()).all()
    modules = LearningModule.query.order_by(LearningModule.created_at.desc()).all()
    return render_template('tpsg/manage_news.html', all_news=all_news, employees=employees, modules=modules, form=form)

@tpsg.route('/delete-news/<int:id>', methods=['POST'])
@login_required
@tpsg_required
def delete_news(id):
    from app.services.news_service import NewsService
    news_item = NewsService.get_news_by_id(id)
    if not news_item:
        flash('Pengumuman tidak ditemukan.', 'danger')
        return redirect(url_for('tpsg.manage_news'))

    success, message = NewsService.delete_news(news_item)
    if success:
        from app.services.audit_service import AuditService
        AuditService.log_delete('News', id, news_item.title)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tpsg.manage_news'))

@tpsg.route('/edit-news/<int:id>', methods=['GET', 'POST'])
@login_required
@tpsg_required
def edit_news(id):
    from app.forms.news_form import NewsForm
    from app.services.news_service import NewsService

    news_item = NewsService.get_news_by_id(id)
    if not news_item:
        flash('Pengumuman tidak ditemukan.', 'danger')
        return redirect(url_for('tpsg.manage_news'))

    form = NewsForm(obj=news_item)

    if request.method == 'POST' and form.validate_on_submit():
        data = {
            'title': form.title.data,
            'category': form.category.data,
            'content': form.content.data,
            'target_type': request.form.get('target_type', 'all'),
            'target_users': request.form.getlist('target_users')
        }
        success, message = NewsService.update_news(news_item, data)
        if success:
            from app.services.audit_service import AuditService
            AuditService.log_update('News', id, data['title'], {'category': data['category']})
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('tpsg.manage_news'))

    employees = Employee.query.order_by(Employee.name.asc()).all()
    return render_template('tpsg/edit_news.html', news_item=news_item, employees=employees, form=form)

@tpsg.route('/generate-dummy')
@login_required
@tpsg_required
def generate_dummy(): 
    return redirect(url_for('tpsg.dashboard'))

# =======================================================
# 7. MANAGE MANUAL CHART DATA
# =======================================================
@tpsg.route('/manage-charts', methods=['GET', 'POST'])
@login_required
@tpsg_required
def manage_charts():
    if request.method == 'POST':
        # 1. Update/Add Batch Stats
        batch_ids = request.form.getlist('batch_id')
        for bid in batch_ids:
            stat = BatchStat.query.get(bid)
            if stat:
                stat.batch_name = request.form.get(f'batch_name_{bid}', stat.batch_name)
                stat.kp3_percent = request.form.get(f'kp3_pct_{bid}')
                stat.kp4_percent = request.form.get(f'kp4_pct_{bid}')
        
        # 2. Handle New Batch Addition
        new_batch_name = request.form.get('new_batch_name')
        if new_batch_name:
            new_stat = BatchStat(
                batch_name=new_batch_name,
                kp3_percent=request.form.get('new_kp3_pct', '0'),
                kp4_percent=request.form.get('new_kp4_pct', '0'),
                participant_count=0
            )
            db.session.add(new_stat)

        try:
            db.session.commit()
            flash('Data grafik berhasil diperbarui!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal memperbarui data: {str(e)}', 'danger')
        
        return redirect(url_for('tpsg.manage_charts'))

    batch_stats = BatchStat.query.all()
    return render_template('tpsg/manage_charts.html', batch_stats=batch_stats)

# =======================================================
# 8. KELOLA MODUL E-LEARNING (MIGRASI OMDD)
# =======================================================
@tpsg.route('/manage-modules', methods=['GET', 'POST'])
@login_required
@tpsg_required
def manage_modules():
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
                from app.services.audit_service import AuditService
                AuditService.log_create('LearningModule', new_module.id, title, {'tps_level': tps_level})
                flash('Modul berhasil diunggah dan disimpan ke sistem!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Terjadi kesalahan saat menyimpan data ke database.', 'danger')
                
            return redirect(url_for('tpsg.manage_news'))

    modules = LearningModule.query.order_by(LearningModule.created_at.desc()).all()
    return render_template('tpsg/manage_modules.html', modules=modules)

@tpsg.route('/delete-module/<int:id>', methods=['POST'])
@login_required
@tpsg_required
def delete_module(id):
    module = LearningModule.query.get_or_404(id)
    try:
        # Hapus file fisik jika ada
        if module.file_name:
            import os as _os
            file_path = os.path.join(current_app.root_path, 'static/uploads/modules', module.file_name)
            if _os.path.exists(file_path):
                _os.remove(file_path)

        db.session.delete(module)
        db.session.commit()
        from app.services.audit_service import AuditService
        AuditService.log_delete('LearningModule', id, module.title)
        flash('Modul berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus modul: {str(e)}', 'danger')
    return redirect(url_for('tpsg.manage_news'))

@tpsg.route('/edit-module/<int:id>', methods=['GET', 'POST'])
@login_required
@tpsg_required
def edit_module(id):
    module = LearningModule.query.get_or_404(id)

    if request.method == 'POST':
        module.title = request.form.get('title')
        module.description = request.form.get('description')
        module.tps_level = request.form.get('tps_level')

        new_file = request.files.get('file')
        if new_file and new_file.filename != '':
            # Hapus file lama
            if module.file_name:
                import os as _os
                old_path = os.path.join(current_app.root_path, 'static/uploads/modules', module.file_name)
                if _os.path.exists(old_path):
                    _os.remove(old_path)

            filename = secure_filename(new_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/modules')
            os.makedirs(upload_folder, exist_ok=True)
            new_file.save(os.path.join(upload_folder, filename))
            module.file_name = filename

        try:
            db.session.commit()
            from app.services.audit_service import AuditService
            AuditService.log_update('LearningModule', id, module.title, {'tps_level': module.tps_level})
            flash('Modul berhasil diperbarui!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal memperbarui: {str(e)}', 'danger')
        return redirect(url_for('tpsg.manage_news'))

    return render_template('tpsg/edit_module.html', module=module)

# =======================================================
# 9. CRUD TRAINING SCHEDULE (FULL) - Using Service Layer + WTForms
# =======================================================
@tpsg.route('/trainings', methods=['GET', 'POST'])
@login_required
@tpsg_required
def manage_trainings():
    from app.forms.training_form import TrainingForm
    from app.services.training_service import TrainingService

    form = TrainingForm()

    if request.method == 'POST' and form.validate_on_submit():
        data = {
            'title': form.title.data,
            'description': form.description.data or '',
            'training_date': form.training_date.data.strftime('%Y-%m-%dT%H:%M') if form.training_date.data else '',
            'location': form.location.data,
            'quota': form.quota.data or 0
        }
        success, _, message = TrainingService.create_training(data)
        if success:
            from app.services.audit_service import AuditService
            AuditService.log_create('Training', None, data['title'], {'location': data['location'], 'quota': data['quota']})
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('tpsg.manage_trainings'))

    trainings = TrainingService.get_all_trainings()
    return render_template('tpsg/manage_trainings.html', trainings=trainings, form=form)

@tpsg.route('/edit-training/<int:id>', methods=['GET', 'POST'])
@login_required
@tpsg_required
def edit_training(id):
    from app.forms.training_form import TrainingForm
    from app.services.training_service import TrainingService

    training = TrainingService.get_training_by_id(id)
    if not training:
        flash('Jadwal training tidak ditemukan.', 'danger')
        return redirect(url_for('tpsg.manage_trainings'))

    form = TrainingForm(obj=training)

    if request.method == 'POST' and form.validate_on_submit():
        data = {
            'title': form.title.data,
            'description': form.description.data or '',
            'training_date': form.training_date.data.strftime('%Y-%m-%dT%H:%M') if form.training_date.data else '',
            'location': form.location.data,
            'quota': form.quota.data or 0
        }
        success, message = TrainingService.update_training(training, data)
        if success:
            from app.services.audit_service import AuditService
            AuditService.log_update('Training', id, data['title'], {'location': data['location']})
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('tpsg.manage_trainings'))

    return render_template('tpsg/edit_training.html', training=training, form=form)

@tpsg.route('/delete-training/<int:id>', methods=['POST'])
@login_required
@tpsg_required
def delete_training(id):
    from app.services.training_service import TrainingService
    training = TrainingService.get_training_by_id(id)
    if not training:
        flash('Jadwal training tidak ditemukan.', 'danger')
        return redirect(url_for('tpsg.manage_trainings'))

    success, message = TrainingService.delete_training(training)
    if success:
        from app.services.audit_service import AuditService
        AuditService.log_delete('Training', id, training.title)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('tpsg.manage_trainings'))