from . import db
from datetime import datetime

# ==========================================
# MODEL 1: TRAINING WORKSHOP
# ==========================================
class Training(db.Model):
    __tablename__ = 'trainings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    training_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    quota = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==========================================
# MODEL 2: ACTIVITY PROGRESS (KAIZEN)
# ==========================================
class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Diubah agar sinkron dengan sistem OMDD
    theme_title = db.Column(db.String(150), nullable=False) 
    
    status = db.Column(db.String(50), default='On Progress') 
    progress_percentage = db.Column(db.Integer, default=0) 
    
    # --- FIELD BARU UNTUK EVALUASI OMDD ---
    file_path = db.Column(db.String(255), nullable=True) 
    score = db.Column(db.Integer, nullable=True) 
    feedback = db.Column(db.Text, nullable=True) 
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow) 
    # --------------------------------------
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relasi balik ke Employee
    employee = db.relationship('Employee', backref=db.backref('activities', lazy=True))

# ==========================================
# MODEL 3: NEWS & SCHEDULE (PENGUMUMAN)
# ==========================================
# ==========================================
# MODEL 3: NEWS & SCHEDULE (PENGUMUMAN)
# ==========================================
class News(db.Model):
    __tablename__ = 'news'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='News')
    content = db.Column(db.Text, nullable=False)
    
    # --- FITUR TARGETED BROADCAST ---
    target_type = db.Column(db.String(50), default='all') # Isinya: 'all' atau 'specific'
    target_users = db.Column(db.Text, nullable=True) # Menyimpan NPK partisipan yang dipilih (pisahkan dengan koma)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)