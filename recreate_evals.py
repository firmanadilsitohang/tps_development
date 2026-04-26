from app import create_app, db
from app.models.employee import WorkshopEvaluation
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("DROP TABLE IF EXISTS workshop_evaluations"))
        db.session.commit()
        print("Dropped workshop_evaluations table successfully.")
    except Exception as e:
        print("Error dropping table:", e)

    try:
        db.create_all()
        print("Recreated tables successfully.")
    except Exception as e:
        print("Error recreating tables:", e)
