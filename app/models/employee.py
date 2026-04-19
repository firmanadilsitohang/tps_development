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
    position = db.Column(db.String(100))
    photo = db.Column(db.String(500), nullable=True) 
    certificate = db.Column(db.String(500), nullable=True)
    current_tps_level = db.Column(db.String(50))
    previous_tps_level = db.Column(db.String(50))
    tahun_lulus_terakhir = db.Column(db.String(20), nullable=True)
    tahun_lulus_saat_ini = db.Column(db.String(20), nullable=True)
    last_activity_theme = db.Column(db.String(200))
    last_activity_type = db.Column(db.String(50))
    batch = db.Column(db.String(50), nullable=True)
    registration_year = db.Column(db.Integer, default=lambda: datetime.utcnow().year)
    status = db.Column(db.String(20), default='pending')
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'))
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))

    workshop_activities = db.relationship('WorkshopActivity', backref='employee', lazy=True, cascade="all, delete-orphan")
    workshop_evaluations = db.relationship('WorkshopEvaluation', backref='employee', lazy=True, cascade="all, delete-orphan")

class WorkshopActivity(db.Model):
    __tablename__ = 'workshop_activities'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    theme_title = db.Column(db.String(200), nullable=False)
    participant_file = db.Column(db.String(255), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending') 
    score = db.Column(db.Integer, default=0)
    feedback = db.Column(db.Text, nullable=True)
    assessed_at = db.Column(db.DateTime, nullable=True)
    assessor_name = db.Column(db.String(100), nullable=True)

class WorkshopEvaluation(db.Model):
    __tablename__ = 'workshop_evaluations'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    score_genba = db.Column(db.Integer, default=0)
    score_problem_solving = db.Column(db.Integer, default=0)
    score_observasi = db.Column(db.Integer, default=0)
    score_kaizen = db.Column(db.Integer, default=0)
    score_implementation = db.Column(db.Integer, default=0)
    score_presentation = db.Column(db.Integer, default=0)
    final_decision = db.Column(db.String(20), default='PASS')
    notes = db.Column(db.Text, nullable=True)
    evaluated_by = db.Column(db.String(100), nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

class BatchStat(db.Model):
    __tablename__ = 'batch_stats'
    id = db.Column(db.Integer, primary_key=True)
    batch_name = db.Column(db.String(50), nullable=False)
    participant_count = db.Column(db.Integer, default=0)
    kp3_count = db.Column(db.Integer, default=0)
    kp4_count = db.Column(db.Integer, default=0)
    kp3_percent = db.Column(db.String(20))
    kp4_percent = db.Column(db.String(20))