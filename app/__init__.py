import click
from flask import Flask, redirect, url_for
from flask.cli import with_appcontext

from config import Config
from app.extensions import db, login_manager, mail, migrate
from app.models import Exercise, Package, SystemConfig, User
from app.utils import format_vnd

def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    app.jinja_env.filters['format_vnd'] = format_vnd

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.query.get(int(user_id)) if user_id else None

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.reception import bp as reception_bp
    from app.blueprints.trainer import bp as trainer_bp
    from app.blueprints.cashier import bp as cashier_bp
    from app.blueprints.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(cashier_bp)
    app.register_blueprint(admin_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.cli.command("seed_db")
    @with_appcontext
    def seed_db() -> None:
        db.create_all()

        users_data = [
            {"username": "admin", "email": "admin@example.com", "role": "admin", "password": "admin123"},
            {"username": "receptionist", "email": "reception@example.com", "role": "receptionist", "password": "reception123"},
            {"username": "trainer", "email": "trainer@example.com", "role": "trainer", "password": "trainer123"},
            {"username": "cashier", "email": "cashier@example.com", "role": "cashier", "password": "cashier123"},
        ]

        for user_data in users_data:
            if not User.query.filter_by(username=user_data["username"]).first():
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    role=user_data["role"]
                )
                user.set_password(user_data["password"])
                db.session.add(user)

        packages = [
            {
                "name": "1 Month",
                "duration_months": 1,
                "price": 500000,
                "description": "Access for one month",
            },
            {
                "name": "3 Months",
                "duration_months": 3,
                "price": 1200000,
                "description": "Discounted quarterly access",
            },
            {
                "name": "6 Months",
                "duration_months": 6,
                "price": 2000000,
                "description": "Half-year membership",
            },
            {
                "name": "12 Months",
                "duration_months": 12,
                "price": 3500000,
                "description": "Full-year membership",
            },
        ]

        for package_data in packages:
            if not Package.query.filter_by(name=package_data["name"]).first():
                db.session.add(Package(**package_data))

        exercises = [
            {
                "name": "Squat",
                "description": "Compound lower body exercise",
                "body_part": "Legs",
            },
            {
                "name": "Bench Press",
                "description": "Compound upper body exercise",
                "body_part": "Chest",
            },
            {
                "name": "Deadlift",
                "description": "Full-body hinge movement",
                "body_part": "Back",
            },
        ]

        for exercise_data in exercises:
            if not Exercise.query.filter_by(name=exercise_data["name"]).first():
                db.session.add(Exercise(**exercise_data))

        if not SystemConfig.query.filter_by(key="max_training_days").first():
            db.session.add(SystemConfig(
                key="max_training_days",
                value="6",
                description="Maximum training days per week for workout plans"
            ))

        db.session.commit()
        click.echo("Database seeded successfully.")

    return app
