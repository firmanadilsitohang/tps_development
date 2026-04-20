from flask import Flask
from flask_login import LoginManager
import os
# AMBIL db DARI FOLDER MODELS (Pusat Database)
from app.models import db 

def create_app():
    app = Flask(__name__)
    
    # --- 1. KONFIGURASI ---
    app.config['SECRET_KEY'] = 'toyota-tpsg-secret-key'
    
    # --- PERBAIKAN: SUNTIK MATI KONEKSI KE MYSQL DI SINI ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/tpsg_db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. INISIALISASI DATABASE ---
    db.init_app(app)
    
    # --- 3. SETUP LOGIN MANAGER ---
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Silakan login terlebih dahulu."
    login_manager.init_app(app)

    # --- 4. USER LOADER ---
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        # Gunakan session.get untuk versi SQLAlchemy terbaru agar lebih aman
        return db.session.get(User, int(user_id))

    # --- 5. REGISTER BLUEPRINT (ROUTES) ---
    # Import dilakukan di dalam fungsi untuk menghindari Circular Import
    from app.routes.auth import auth
    from app.routes.participant import participant
    from app.routes.omdd import omdd
    from app.routes.tpsg import tpsg
    from app.routes.management import management
    
    # Daftarkan semua ke aplikasi
    app.register_blueprint(auth)
    app.register_blueprint(participant)
    app.register_blueprint(omdd)
    app.register_blueprint(tpsg)
    app.register_blueprint(management)

    return app