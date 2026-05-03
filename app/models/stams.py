from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import enum

class ProjectStatus(enum.Enum):
    IDLE = 'Idle'
    ON_PROGRESS = 'On Progress'
    COMPLETED = 'Completed'
    OVERDUE = 'Overdue'

class Department(db.Model):
    __tablename__ = 'stams_departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_cost = db.Column(db.BigInteger, default=0)
    target_time = db.Column(db.Integer, default=0)
    actual_cost = db.Column(db.BigInteger, default=0)
    actual_time = db.Column(db.Integer, default=0)
    
    sections = db.relationship('Section', backref='stams_department', lazy=True)
    users = db.relationship('UserSTAMS', backref='stams_department', lazy=True)

class Section(db.Model):
    __tablename__ = 'stams_sections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey('stams_departments.id'), nullable=False)
    
    users = db.relationship('UserSTAMS', backref='stams_section', lazy=True)

class UserSTAMS(UserMixin, db.Model):
    __tablename__ = 'stams_users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # Agent, Section Head, Dept Head, TPSG
    section_id = db.Column(db.Integer, db.ForeignKey('stams_sections.id'))
    dept_id = db.Column(db.Integer, db.ForeignKey('stams_departments.id'))
    
    projects = db.relationship('Project', backref='agent', lazy=True)
    workshop_progress = db.relationship('WorkshopProgress', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class WorkshopProgress(db.Model):
    __tablename__ = 'workshop_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('stams_users.id'), nullable=False)
    ws_1 = db.Column(db.Integer, default=0)
    ws_2 = db.Column(db.Integer, default=0)
    ws_3 = db.Column(db.Integer, default=0)
    ws_4 = db.Column(db.Integer, default=0)
    ws_5 = db.Column(db.Integer, default=0)
    ws_6 = db.Column(db.Integer, default=0)
    ws_7 = db.Column(db.Integer, default=0)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('stams_users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category_4m = db.Column(db.String(50), nullable=False) # Man, Material, Machine, Methode
    start_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date)
    target_date = db.Column(db.Date, nullable=False)
    actual_end_date = db.Column(db.Date)
    reduce_time_sec = db.Column(db.Integer, default=0)
    reduce_cost_rp = db.Column(db.BigInteger, default=0)
    status = db.Column(db.String(20), default='Idle') # Idle, On Progress, Completed, Overdue

    def update_overdue_status(self):
        """Utility to check and return if project is overdue"""
        if self.status == 'On Progress' and self.target_date < datetime.now(timezone.utc).date():
            return 'Overdue'
        return self.status
