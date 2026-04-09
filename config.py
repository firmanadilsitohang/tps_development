import os

class Config:
    SECRET_KEY = 'tps-secret-key-2026'
    
    # KITA KUNCI MATI LANGSUNG KE MYSQL DI SINI:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/tpsg_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024