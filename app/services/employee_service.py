"""
Service layer for Employee operations.
Separates business logic from routes.
"""
from datetime import datetime
from app import db
from app.models.employee import Employee, Plant, Division, Department
from werkzeug.security import generate_password_hash


def sanitize(text, max_length=None):
    """Sanitize text input to prevent XSS."""
    from app.services.security import sanitize_text
    return sanitize_text(text, max_length) if text else text


class EmployeeService:
    """Business logic for Employee operations."""

    @staticmethod
    def get_all_employees(status_filter=None):
        """Get all employees with optional status filter."""
        query = Employee.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        return query.order_by(Employee.name.asc()).all()

    @staticmethod
    def get_employee_by_id(employee_id):
        """Get employee by ID."""
        return Employee.query.get(employee_id)

    @staticmethod
    def get_employee_by_username(username):
        """Get employee by username (NIK)."""
        return Employee.query.filter_by(username=username).first()

    @staticmethod
    def calculate_age(birth_date, reference_year=None):
        """Calculate age from birth date."""
        from datetime import date
        if reference_year is None:
            reference_year = date.today().year
        if birth_date:
            return reference_year - birth_date.year
        return 0

    @staticmethod
    def calculate_retirement_year(birth_date):
        """Calculate retirement year (birth_year + 55)."""
        if birth_date:
            return birth_date.year + 55
        return None

    @staticmethod
    def update_employee(employee, data):
        """
        Update employee data from form data dictionary.
        Returns (success: bool, message: str)
        """
        try:
            # Update basic fields
            if 'name' in data:
                employee.name = sanitize(data['name'], 100)

            if 'username' in data:
                new_username = sanitize(data['username'], 20)
                if new_username != employee.username:
                    employee.username = new_username
                    if employee.user:
                        employee.user.username = new_username

            if 'birth_date' in data and data['birth_date']:
                employee.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()

            if 'position' in data:
                employee.position = sanitize(data['position'], 100)

            # Handle Plant
            if 'plant' in data and data['plant']:
                plant = Plant.query.filter_by(name=data['plant']).first()
                if not plant:
                    plant = Plant(name=sanitize(data['plant'], 50))
                    db.session.add(plant)
                    db.session.flush()
                employee.plant_id = plant.id

            # Handle Division
            if 'division' in data and data['division']:
                div = Division.query.filter_by(name=data['division']).first()
                if not div:
                    div = Division(name=sanitize(data['division'], 50))
                    db.session.add(div)
                    db.session.flush()
                employee.division_id = div.id

            # Handle Department
            if 'department' in data and data['department']:
                dept = Department.query.filter_by(name=data['department']).first()
                if not dept:
                    dept = Department(name=sanitize(data['department'], 50))
                    db.session.add(dept)
                    db.session.flush()
                employee.department_id = dept.id

            # Handle password
            if 'password' in data and data['password'] and employee.user:
                employee.user.password = generate_password_hash(data['password'])

            # Update TPS fields
            if 'previous_tps_level' in data:
                employee.previous_tps_level = sanitize(data['previous_tps_level'], 50)
            if 'tahun_lulus_terakhir' in data:
                employee.tahun_lulus_terakhir = sanitize(data['tahun_lulus_terakhir'], 10)
            if 'current_tps_level' in data:
                employee.current_tps_level = sanitize(data['current_tps_level'], 50)
            if 'tahun_lulus_saat_ini' in data:
                employee.tahun_lulus_saat_ini = sanitize(data['tahun_lulus_saat_ini'], 10)
            if 'last_activity_type' in data:
                employee.last_activity_type = sanitize(data['last_activity_type'], 50)
            if 'last_activity_theme' in data:
                employee.last_activity_theme = sanitize(data['last_activity_theme'], 200)
            if 'batch' in data:
                employee.batch = sanitize(data['batch'], 20)

            db.session.commit()
            return True, "Employee updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete_employees(employee_ids):
        """
        Delete multiple employees by ID.
        Returns (success: bool, count: int, message: str)
        """
        try:
            from app.models.user import User
            for emp_id in employee_ids:
                # Delete related user first
                User.query.filter_by(employee_id=emp_id).delete()

            count = Employee.query.filter(Employee.id.in_(employee_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
            return True, count, f"{count} employees deleted"
        except Exception as e:
            db.session.rollback()
            return False, 0, str(e)

    @staticmethod
    def reset_all():
        """Delete all employees and related users."""
        try:
            from app.models.user import User
            User.query.filter(User.employee_id.isnot(None)).delete()
            Employee.query.delete()
            db.session.commit()
            return True, "All employees reset"
        except Exception as e:
            db.session.rollback()
            return False, str(e)


class OrganizationService:
    """Business logic for Organization (Plant/Division/Department) operations."""

    @staticmethod
    def get_or_create_plant(name):
        """Get existing or create new Plant."""
        plant = Plant.query.filter_by(name=name).first()
        if not plant:
            plant = Plant(name=name)
            db.session.add(plant)
            db.session.flush()
        return plant

    @staticmethod
    def get_or_create_division(name):
        """Get existing or create new Division."""
        div = Division.query.filter_by(name=name).first()
        if not div:
            div = Division(name=name)
            db.session.add(div)
            db.session.flush()
        return div

    @staticmethod
    def get_or_create_department(name):
        """Get existing or create new Department."""
        dept = Department.query.filter_by(name=name).first()
        if not dept:
            dept = Department(name=name)
            db.session.add(dept)
            db.session.flush()
        return dept
