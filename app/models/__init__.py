from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    workout_plans = db.relationship("WorkoutPlan", back_populates="trainer")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active_user(self) -> bool:
        return self.is_active

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)

    invoices = db.relationship("Invoice", back_populates="package")

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    body_part = db.Column(db.String(100))

    workout_details = db.relationship("WorkoutDetail", back_populates="exercise")

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    active_until = db.Column(db.Date, nullable=True)

    invoices = db.relationship("Invoice", back_populates="member", cascade="all, delete-orphan")
    workout_plans = db.relationship(
        "WorkoutPlan", back_populates="member", cascade="all, delete-orphan"
    )

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey("package.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    member = db.relationship("Member", back_populates="invoices")
    package = db.relationship("Package", back_populates="invoices")

class WorkoutPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    trainer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text)

    member = db.relationship("Member", back_populates="workout_plans")
    trainer = db.relationship("User", back_populates="workout_plans")
    workout_details = db.relationship(
        "WorkoutDetail", back_populates="plan", cascade="all, delete-orphan"
    )

class WorkoutDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("workout_plan.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise.id"), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.String(50), nullable=False)
    schedule_day = db.Column(db.String(100), nullable=False)

    plan = db.relationship("WorkoutPlan", back_populates="workout_details")
    exercise = db.relationship("Exercise", back_populates="workout_details")

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    @staticmethod
    def get_config(key: str, default: str = None) -> str:
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            return config.value
        return default

    @staticmethod
    def set_config(key: str, value: str, description: str = None) -> "SystemConfig":
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
            if description is not None:
                config.description = description
        else:
            config = SystemConfig(key=key, value=value, description=description)
            db.session.add(config)
        db.session.commit()
        return config
