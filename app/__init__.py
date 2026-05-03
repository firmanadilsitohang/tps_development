from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv

load_dotenv()

from app.models import db

# --- RATE LIMITER SETUP (before create_app to avoid circular imports) ---
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['WTF_CSRF_ENABLED'] = True

    # --- PERBAIKAN: SUNTIK MATI KONEKSI KE MYSQL DI SINI ---
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/tpsg_db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # --- 2. INISIALISASI DATABASE ---
    db.init_app(app)

    # --- 3. SETUP FLASK-MIGRATE ---
    migrate = Migrate()
    migrate.init_app(app, db)

    # --- 4. SETUP CSRF PROTECTION ---
    csrf = CSRFProtect()
    csrf.init_app(app)

    # --- 5. SETUP RATE LIMITING ---
    limiter.init_app(app)

    # --- 5. SETUP LOGIN MANAGER ---
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Silakan login terlebih dahulu."
    login_manager.init_app(app)

    # --- 6. USER LOADER ---
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- 7. REGISTER BLUEPRINT (ROUTES) ---
    from app.routes.auth import auth
    from app.routes.tpsg import tpsg
    from app.routes.audit import audit_bp as audit
    from app.routes.agent import agent_bp
    from app.routes.api import api_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth)
    app.register_blueprint(tpsg)
    app.register_blueprint(audit)
    app.register_blueprint(agent_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    # --- 8. CENTRALIZED ERROR HANDLERS ---
    @app.errorhandler(404)
    def not_found_error(e):
        from flask import render_template, request
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template, request
        db.session.rollback()  # Rollback any pending transactions
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(e):
        from flask import render_template, request
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(429)
    def rate_limit_error(e):
        from flask import render_template, request
        if request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        return render_template('errors/429.html'), 429

    return app