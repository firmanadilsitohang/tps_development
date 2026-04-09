from . import db
from datetime import datetime

class Plant(db.Model):
    __tablename__ = 'plants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    employees = db.relationship('Employee', backref='plant', lazy=True)

class Division(db.Model):
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    employees = db.relationship('Employee', backref='division', lazy=True)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    employees = db.relationship('Employee', backref='department', lazy=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False) # NIK
    birth_date = db.Column(db.Date)
    position = db.Column(db.String(50))
    
    # Kolom untuk Foto dan Sertifikat
    photo = db.Column(db.String(500), nullable=True) 
    certificate = db.Column(db.String(100))
    
    # Kompetensi
    current_tps_level = db.Column(db.String(50))
    previous_tps_level = db.Column(db.String(50))
    tahun_lulus_terakhir = db.Column(db.String(20), nullable=True)
    tahun_lulus_saat_ini = db.Column(db.String(20), nullable=True)
    
    # Aktivitas Terakhir
    last_activity_theme = db.Column(db.String(200))
    last_activity_type = db.Column(db.String(50))
    batch = db.Column(db.String(50), nullable=True)
    
    # === FITUR BARU: TAHUN REGISTRASI UNTUK GRAFIK HISTORI BOD ===
    # Otomatis merekam tahun saat data dimasukkan
    registration_year = db.Column(db.Integer, default=lambda: datetime.utcnow().year)
    
    status = db.Column(db.String(20), default='pending')
    
    # Foreign Keys
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'))
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))

    # === RELASI BARU: MENGHUBUNGKAN KARYAWAN KE TUGAS/WORKSHOP-NYA ===
    # Jika karyawan dihapus, semua tugas/nilainya ikut terhapus otomatis
    workshop_activities = db.relationship('WorkshopActivity', backref='employee_data', lazy=True, cascade="all, delete-orphan")

# =========================================================
# TABEL BARU: INTERAKSI PESERTA & OMDD (PORTAL WORKSHOP)
# =========================================================
class WorkshopActivity(db.Model):
    __tablename__ = 'workshop_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # --- BAGIAN PESERTA (UPLOAD TUGAS) ---
    theme_title = db.Column(db.String(200), nullable=False)
    participant_file = db.Column(db.String(255), nullable=True) # Nama file excel/ppt/pdf yg diupload
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- BAGIAN OMDD (PENILAIAN & FEEDBACK) ---
    # Status: 'pending' (baru upload), 'revision' (butuh perbaikan), 'approved' (lulus)
    status = db.Column(db.String(20), default='pending') 
    score = db.Column(db.Float, nullable=True) # Nilai Angka dari OMDD
    feedback = db.Column(db.Text, nullable=True) # Catatan detail dari OMDD
    assessed_at = db.Column(db.DateTime, nullable=True) # Waktu OMDD menilai
    assessor_name = db.Column(db.String(100), nullable=True) # Nama OMDD yang menilai