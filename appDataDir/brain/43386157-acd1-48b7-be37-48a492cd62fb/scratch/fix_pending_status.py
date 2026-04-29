from app import app, db
from app.models.employee import Employee

with app.app_context():
    # Set all 'pending' employees to 'active'
    pending_emps = Employee.query.filter_by(status='pending').all()
    count = len(pending_emps)
    for emp in pending_emps:
        emp.status = 'active'
    
    db.session.commit()
    print(f"Successfully updated {count} employees from 'pending' to 'active'.")
