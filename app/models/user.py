from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False) # Ini untuk NIK
    password = db.Column(db.String(255), nullable=False)
    
    # --- UPDATE ROLE BERDASARKAN GRAND DESIGN ---
    # Role yang tersedia: 
    # 1. 'tpsg' (Admin Sistem)
    # 2. 'omdd' (Assessor Lapangan)
    # 3. 'participant' (Peserta Workshop)
    # 4. 'bod' (Direktur - Bisa lihat semua Divisi)
    # 5. 'division_head' (Kadiv - Hanya lihat Divisi miliknya)
    role = db.Column(db.String(20), default='participant') 
    
    is_first_login = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # RELASI KE EMPLOYEE
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # JEMBATAN PENGHUBUNG 
    employee = db.relationship('Employee', backref=db.backref('user', uselist=False))
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password, password)