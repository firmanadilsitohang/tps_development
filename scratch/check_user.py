from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='MANAGEMENT001').first()
    if user:
        print(f"User found: {user.username}, Role: {user.role}")
    else:
        print("User MANAGEMENT001 NOT found in database.")
