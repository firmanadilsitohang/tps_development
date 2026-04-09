import os
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app.models.user import User
from app.models.employee import Employee, Plant, Division, Department
from app import db

# TAMBAHKAN url_prefix='/auth' agar alamatnya jadi /auth/login
auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/')
## Belum ditambahkan halaman


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect cerdas berdasarkan ROLE
        if current_user.role == 'tpsg':
            return redirect(url_for('tpsg.dashboard'))
        elif current_user.role == 'omdd':
            return redirect(url_for('omdd.dashboard'))
        else:
            return redirect(url_for('participant.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Redirect setelah berhasil login
            if user.role == 'tpsg':
                return redirect(url_for('tpsg.dashboard'))
            elif user.role == 'omdd':
                return redirect(url_for('omdd.dashboard'))
            else:
                return redirect(url_for('participant.dashboard'))
        
        flash('NIK atau Password salah. Silakan coba lagi.', 'danger')
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username') # NIK
        password = request.form.get('password')
        
        current_tps = request.form.get('current_tps_level')
        prev_tps = request.form.get('previous_tps_level')
        
        # --- FITUR BARU: MENANGKAP DATA TAHUN LULUS ---
        tahun_lulus_terakhir = request.form.get('tahun_lulus_terakhir')
        tahun_lulus_saat_ini = request.form.get('tahun_lulus_saat_ini')
        
        act_theme = request.form.get('last_activity_theme')
        act_type = request.form.get('last_activity_type')
        
        # --- MENANGKAP DATA BATCH (Bisa String/Simbol #) ---
        batch = request.form.get('batch') 
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('NIK sudah terdaftar dalam sistem.', 'danger')
            return redirect(url_for('auth.register'))

        try:
            # --- PROSES UPLOAD FILE ---
            photo_file = request.files.get('photo')
            cert_file = request.files.get('certificate')
            
            photo_filename = None
            cert_filename = None

            # Path absolut yang lebih aman
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            photo_path = os.path.join(root_dir, 'static', 'uploads', 'photos')
            cert_path = os.path.join(root_dir, 'static', 'uploads', 'certificates')
            
            for p in [photo_path, cert_path]:
                if not os.path.exists(p):
                    os.makedirs(p)

            if photo_file and photo_file.filename != '':
                ext = photo_file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f"photo_{username}.{ext}"
                photo_file.save(os.path.join(photo_path, photo_filename))

            if cert_file and cert_file.filename != '':
                ext = cert_file.filename.rsplit('.', 1)[1].lower()
                cert_filename = f"cert_{username}.{ext}"
                cert_file.save(os.path.join(cert_path, cert_filename))

            # --- LOGIKA ORGANISASI ---
            plant_name = request.form.get('plant')
            div_name = request.form.get('division')
            dept_name = request.form.get('department')

            plant = Plant.query.filter_by(name=plant_name).first()
            if not plant and plant_name:
                plant = Plant(name=plant_name); db.session.add(plant)
            
            division = Division.query.filter_by(name=div_name).first()
            if not division and div_name:
                division = Division(name=div_name); db.session.add(division)

            department = Department.query.filter_by(name=dept_name).first()
            if not department and dept_name:
                department = Department(name=dept_name); db.session.add(department)
            
            db.session.flush()

            # --- BUAT DATA EMPLOYEE ---
            new_emp = Employee(
                name=name,
                username=username,
                photo=photo_filename,
                certificate=cert_filename,
                birth_date=datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d') if request.form.get('birth_date') else None,
                position=request.form.get('position'),
                current_tps_level=current_tps,
                previous_tps_level=prev_tps,
                
                # MENYIMPAN DATA TAHUN LULUS KE DATABASE
                tahun_lulus_terakhir=tahun_lulus_terakhir,
                tahun_lulus_saat_ini=tahun_lulus_saat_ini,
                
                last_activity_theme=act_theme,
                last_activity_type=act_type,
                batch=batch, # MENYIMPAN DATA BATCH KE DATABASE
                plant_id=plant.id if plant else None,
                division_id=division.id if division else None,
                department_id=department.id if department else None,
                
                # UBAH STATUS MENJADI PENDING AGAR MASUK ANTREAN APPROVAL
                status='pending' 
            )
            db.session.add(new_emp)
            db.session.flush() 

            # --- BUAT DATA USER ---
            new_user = User(
                username=username,
                role='participant',
                employee_id=new_emp.id
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()

            flash('Registrasi berhasil! Menunggu persetujuan Admin TPS-G.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal registrasi: {str(e)}', 'danger')

    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# PEMBUAT AKUN OMDD (Jalur Cepat untuk Tes)
@auth.route('/setup-omdd')
def setup_omdd():
    user = User.query.filter_by(username='OMDD001').first()
    if not user:
        new_omdd = User(username='OMDD001', role='omdd')
        new_omdd.set_password('tmmin123')
        db.session.add(new_omdd)
        db.session.commit()
        return "<h3>✅ Akun OMDD Berhasil Dibuat!<br>User: OMDD001<br>Pass: tmmin123</h3>"
    return "<h3>Akun OMDD sudah ada.</h3>"