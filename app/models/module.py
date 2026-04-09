from . import db
from datetime import datetime

class LearningModule(db.Model):
    __tablename__ = 'learning_modules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tps_level = db.Column(db.String(50), nullable=False) # Contoh: 'STEP UP', 'ADVANCE', 'KP3', 'KP4', atau 'ALL'
    file_name = db.Column(db.String(255), nullable=False) # Nama file PDF/Video yang diupload
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<LearningModule {self.title} - {self.tps_level}>"