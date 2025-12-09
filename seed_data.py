"""
Seed script to populate the database with sample data.
Run with: python seed_data.py
"""

from datetime import date, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Exercise,
    Invoice,
    Member,
    Package,
    SystemConfig,
    User,
    WorkoutDetail,
    WorkoutPlan,
)


def seed_users():
    """Create sample users with different roles."""
    users = [
        {"username": "admin", "email": "admin@gym.com", "password": "admin123", "role": "admin"},
        {"username": "trainer1", "email": "trainer1@gym.com", "password": "trainer123", "role": "trainer"},
        {"username": "trainer2", "email": "trainer2@gym.com", "password": "trainer123", "role": "trainer"},
        {"username": "cashier", "email": "cashier@gym.com", "password": "cashier123", "role": "cashier"},
        {"username": "reception", "email": "reception@gym.com", "password": "reception123", "role": "reception"},
    ]

    created_users = []
    for user_data in users:
        user = User.query.filter_by(username=user_data["username"]).first()
        if not user:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                role=user_data["role"],
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            print(f"Created user: {user_data['username']}")
        created_users.append(user)

    db.session.commit()
    return created_users


def seed_packages():
    """Create sample gym packages."""
    packages = [
        {"name": "Basic Monthly", "duration_months": 1, "price": 500000.00, "description": "Basic gym access for 1 month"},
        {"name": "Standard Quarterly", "duration_months": 3, "price": 1300000.00, "description": "Full gym access for 3 months"},
        {"name": "Premium Semi-Annual", "duration_months": 6, "price": 2400000.00, "description": "Premium access with trainer sessions for 6 months"},
        {"name": "VIP Annual", "duration_months": 12, "price": 4500000.00, "description": "VIP access with unlimited trainer sessions for 1 year"},
    ]

    created_packages = []
    for pkg_data in packages:
        pkg = Package.query.filter_by(name=pkg_data["name"]).first()
        if not pkg:
            pkg = Package(**pkg_data)
            db.session.add(pkg)
            print(f"Created package: {pkg_data['name']}")
        created_packages.append(pkg)

    db.session.commit()
    return created_packages


def seed_exercises():
    """Create sample exercises."""
    exercises = [
        {"name": "Bench Press", "description": "Chest press on flat bench", "body_part": "Chest"},
        {"name": "Squat", "description": "Barbell back squat", "body_part": "Legs"},
        {"name": "Deadlift", "description": "Conventional deadlift", "body_part": "Back"},
        {"name": "Shoulder Press", "description": "Overhead barbell press", "body_part": "Shoulders"},
        {"name": "Bicep Curl", "description": "Dumbbell bicep curl", "body_part": "Arms"},
        {"name": "Tricep Dip", "description": "Parallel bar dips", "body_part": "Arms"},
        {"name": "Lat Pulldown", "description": "Cable lat pulldown", "body_part": "Back"},
        {"name": "Leg Press", "description": "Machine leg press", "body_part": "Legs"},
        {"name": "Plank", "description": "Core stability hold", "body_part": "Core"},
        {"name": "Lunges", "description": "Walking lunges", "body_part": "Legs"},
    ]

    created_exercises = []
    for ex_data in exercises:
        ex = Exercise.query.filter_by(name=ex_data["name"]).first()
        if not ex:
            ex = Exercise(**ex_data)
            db.session.add(ex)
            print(f"Created exercise: {ex_data['name']}")
        created_exercises.append(ex)

    db.session.commit()
    return created_exercises


def seed_members():
    """Create sample gym members."""
    members = [
        {"full_name": "John Smith", "gender": "Male", "dob": date(1990, 5, 15), "phone": "555-0101", "email": "john.smith@email.com"},
        {"full_name": "Jane Doe", "gender": "Female", "dob": date(1988, 8, 22), "phone": "555-0102", "email": "jane.doe@email.com"},
        {"full_name": "Mike Johnson", "gender": "Male", "dob": date(1995, 3, 10), "phone": "555-0103", "email": "mike.j@email.com"},
        {"full_name": "Sarah Williams", "gender": "Female", "dob": date(1992, 11, 5), "phone": "555-0104", "email": "sarah.w@email.com"},
        {"full_name": "David Brown", "gender": "Male", "dob": date(1985, 7, 30), "phone": "555-0105", "email": "david.b@email.com"},
    ]

    created_members = []
    for member_data in members:
        member = Member.query.filter_by(email=member_data["email"]).first()
        if not member:
            member = Member(
                **member_data,
                active_until=date.today() + timedelta(days=90),
            )
            db.session.add(member)
            print(f"Created member: {member_data['full_name']}")
        created_members.append(member)

    db.session.commit()
    return created_members


def seed_invoices(members, packages):
    """Create sample invoices."""
    if not members or not packages:
        print("Skipping invoices - no members or packages")
        return []

    created_invoices = []
    for i, member in enumerate(members):
        pkg = packages[i % len(packages)]
        existing = Invoice.query.filter_by(member_id=member.id, package_id=pkg.id).first()
        if not existing:
            invoice = Invoice(
                member_id=member.id,
                package_id=pkg.id,
                amount=pkg.price,
            )
            db.session.add(invoice)
            print(f"Created invoice for: {member.full_name}")
            created_invoices.append(invoice)

    db.session.commit()
    return created_invoices


def seed_workout_plans(members, trainers, exercises):
    """Create sample workout plans with details."""
    if not members or not trainers or not exercises:
        print("Skipping workout plans - missing data")
        return

    trainer_users = [u for u in trainers if u.role == "trainer"]
    if not trainer_users:
        print("No trainers found")
        return

    days = ["Monday", "Wednesday", "Friday"]

    for i, member in enumerate(members[:3]):
        trainer = trainer_users[i % len(trainer_users)]
        existing = WorkoutPlan.query.filter_by(member_id=member.id).first()
        if not existing:
            plan = WorkoutPlan(
                member_id=member.id,
                trainer_id=trainer.id,
                notes=f"Custom workout plan for {member.full_name}",
            )
            db.session.add(plan)
            db.session.flush()

            for j, day in enumerate(days):
                for k in range(3):
                    ex = exercises[(j * 3 + k) % len(exercises)]
                    detail = WorkoutDetail(
                        plan_id=plan.id,
                        exercise_id=ex.id,
                        sets=3,
                        reps="10-12",
                        schedule_day=day,
                    )
                    db.session.add(detail)

            print(f"Created workout plan for: {member.full_name}")

    db.session.commit()


def seed_system_config():
    """Create default system configuration."""
    configs = [
        {"key": "gym_name", "value": "FitLife Gym", "description": "Name of the gym"},
        {"key": "gym_email", "value": "contact@fitlifegym.com", "description": "Contact email"},
        {"key": "gym_phone", "value": "555-GYM-FIT", "description": "Contact phone"},
        {"key": "currency", "value": "USD", "description": "Default currency"},
    ]

    for cfg in configs:
        existing = SystemConfig.query.filter_by(key=cfg["key"]).first()
        if not existing:
            SystemConfig.set_config(cfg["key"], cfg["value"], cfg["description"])
            print(f"Created config: {cfg['key']}")


def seed_all():
    """Run all seed functions."""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)

    users = seed_users()
    packages = seed_packages()
    exercises = seed_exercises()
    members = seed_members()
    seed_invoices(members, packages)
    seed_workout_plans(members, users, exercises)
    seed_system_config()

    print("=" * 50)
    print("Database seeding completed!")
    print("=" * 50)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_all()
