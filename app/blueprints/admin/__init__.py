from __future__ import annotations

import calendar
from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from flask_login import current_user

from app.extensions import db
from app.models import Exercise, Invoice, Member, Package, SystemConfig, User, WorkoutDetail

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.route("/dashboard")
@login_required
def dashboard():
    user_count = User.query.count()
    package_count = Package.query.count()
    exercise_count = Exercise.query.count()
    
    return render_template(
        "admin/dashboard.html",
        user_count=user_count,
        package_count=package_count,
        exercise_count=exercise_count
    )

@bp.route("/api/revenue_data")
@login_required
def revenue_data():
    current_year = datetime.utcnow().year
    monthly_totals = [0] * 12

    results = (
        db.session.query(
            db.func.extract("month", Invoice.created_at).label("month"),
            db.func.sum(Invoice.amount).label("total"),
        )
        .filter(db.func.extract("year", Invoice.created_at) == current_year)
        .group_by("month")
        .order_by("month")
        .all()
    )

    for row in results:
        month_index = int(row.month) - 1
        monthly_totals[month_index] = float(row.total)

    labels = [calendar.month_abbr[i] for i in range(1, 13)]
    return jsonify({"labels": labels, "data": monthly_totals})

@bp.route("/api/active_members")
@login_required
def active_members():
    today = date.today()
    count = Member.query.filter(Member.active_until >= today).count()
    return jsonify({"count": count})

@bp.route("/api/members_per_package")
@login_required
def members_per_package():
    today = date.today()
    
    active_members_list = Member.query.filter(Member.active_until >= today).all()
    
    package_counts = {}
    for member in active_members_list:
        latest_invoice = (
            Invoice.query
            .filter(Invoice.member_id == member.id)
            .order_by(Invoice.created_at.desc())
            .first()
        )
        if latest_invoice and latest_invoice.package:
            package_name = latest_invoice.package.name
            package_counts[package_name] = package_counts.get(package_name, 0) + 1
    
    labels = list(package_counts.keys())
    data = list(package_counts.values())
    
    return jsonify({"labels": labels, "data": data})

@bp.route("/packages", methods=["GET"])
@login_required
def packages():
    all_packages = Package.query.order_by(Package.duration_months).all()
    return render_template("admin/packages.html", packages=all_packages)

@bp.route("/packages", methods=["POST"])
@login_required
def create_package():
    name = request.form.get("name", "").strip()
    duration_months = request.form.get("duration_months", type=int)
    price = request.form.get("price", type=float)
    description = request.form.get("description", "").strip()

    if not name:
        flash("Tên gói tập là bắt buộc.", "danger")
        return redirect(url_for("admin.packages"))
    
    if not duration_months or duration_months < 1:
        flash("Thời hạn phải ít nhất 1 tháng.", "danger")
        return redirect(url_for("admin.packages"))
    
    if not price or price < 0:
        flash("Giá phải là số dương.", "danger")
        return redirect(url_for("admin.packages"))

    package = Package(
        name=name,
        duration_months=duration_months,
        price=price,
        description=description if description else None
    )
    db.session.add(package)
    db.session.commit()

    flash(f"Tạo gói tập '{name}' thành công.", "success")
    return redirect(url_for("admin.packages"))

@bp.route("/packages/<int:id>/edit", methods=["GET"])
@login_required
def edit_package(id):
    package = Package.query.get_or_404(id)
    return render_template("admin/package_edit.html", package=package)

@bp.route("/packages/<int:id>/edit", methods=["POST"])
@login_required
def update_package(id):
    package = Package.query.get_or_404(id)
    
    name = request.form.get("name", "").strip()
    duration_months = request.form.get("duration_months", type=int)
    price = request.form.get("price", type=float)
    description = request.form.get("description", "").strip()

    if not name:
        flash("Tên gói tập là bắt buộc.", "danger")
        return redirect(url_for("admin.edit_package", id=id))
    
    if not duration_months or duration_months < 1:
        flash("Thời hạn phải ít nhất 1 tháng.", "danger")
        return redirect(url_for("admin.edit_package", id=id))
    
    if not price or price < 0:
        flash("Giá phải là số dương.", "danger")
        return redirect(url_for("admin.edit_package", id=id))

    package.name = name
    package.duration_months = duration_months
    package.price = price
    package.description = description if description else None
    db.session.commit()

    flash(f"Cập nhật gói tập '{name}' thành công.", "success")
    return redirect(url_for("admin.packages"))

@bp.route("/packages/<int:id>/delete", methods=["POST"])
@login_required
def delete_package(id):
    package = Package.query.get_or_404(id)
    
    invoice_count = Invoice.query.filter_by(package_id=id).count()
    if invoice_count > 0:
        flash("Không thể xóa gói tập đã có hóa đơn.", "danger")
        return redirect(url_for("admin.packages"))
    
    package_name = package.name
    db.session.delete(package)
    db.session.commit()
    
    flash(f"Đã xóa gói tập '{package_name}'.", "success")
    return redirect(url_for("admin.packages"))

@bp.route("/exercises", methods=["GET"])
@login_required
def exercises():
    all_exercises = Exercise.query.order_by(Exercise.name).all()
    return render_template("admin/exercises.html", exercises=all_exercises)

@bp.route("/exercises", methods=["POST"])
@login_required
def create_exercise():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    body_part = request.form.get("body_part", "").strip()

    if not name:
        flash("Tên bài tập là bắt buộc.", "danger")
        return redirect(url_for("admin.exercises"))

    exercise = Exercise(
        name=name,
        description=description if description else None,
        body_part=body_part if body_part else None,
    )
    db.session.add(exercise)
    db.session.commit()

    flash(f"Tạo bài tập '{name}' thành công.", "success")
    return redirect(url_for("admin.exercises"))

@bp.route("/exercises/<int:id>/edit", methods=["GET"])
@login_required
def edit_exercise(id):
    exercise = Exercise.query.get_or_404(id)
    return render_template("admin/exercise_edit.html", exercise=exercise)

@bp.route("/exercises/<int:id>/edit", methods=["POST"])
@login_required
def update_exercise(id):
    exercise = Exercise.query.get_or_404(id)

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    body_part = request.form.get("body_part", "").strip()

    if not name:
        flash("Tên bài tập là bắt buộc.", "danger")
        return redirect(url_for("admin.edit_exercise", id=id))

    exercise.name = name
    exercise.description = description if description else None
    exercise.body_part = body_part if body_part else None
    db.session.commit()

    flash(f"Cập nhật bài tập '{name}' thành công.", "success")
    return redirect(url_for("admin.exercises"))

@bp.route("/exercises/<int:id>/delete", methods=["POST"])
@login_required
def delete_exercise(id):
    exercise = Exercise.query.get_or_404(id)

    workout_detail_count = WorkoutDetail.query.filter_by(exercise_id=id).count()
    if workout_detail_count > 0:
        flash("Không thể xóa bài tập đang được sử dụng trong lịch tập.", "danger")
        return redirect(url_for("admin.exercises"))

    exercise_name = exercise.name
    db.session.delete(exercise)
    db.session.commit()

    flash(f"Đã xóa bài tập '{exercise_name}'.", "success")
    return redirect(url_for("admin.exercises"))

@bp.route("/settings", methods=["GET"])
@login_required
def settings():
    max_training_days = SystemConfig.get_config("max_training_days", "6")
    return render_template("admin/settings.html", max_training_days=max_training_days)

@bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    max_training_days = request.form.get("max_training_days", type=int)

    if max_training_days is None or max_training_days < 1 or max_training_days > 7:
        flash("Số ngày tập tối đa phải từ 1 đến 7.", "danger")
        return redirect(url_for("admin.settings"))

    SystemConfig.set_config(
        key="max_training_days",
        value=str(max_training_days),
        description="Số ngày tập tối đa mỗi tuần"
    )

    flash("Cập nhật cài đặt thành công.", "success")
    return redirect(url_for("admin.settings"))

@bp.route("/users", methods=["GET"])
@login_required
def users():
    all_users = User.query.order_by(User.role, User.username).all()
    return render_template("admin/users.html", users=all_users)

@bp.route("/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()

        errors = []
        if not username:
            errors.append("Tên đăng nhập là bắt buộc.")
        if not email:
            errors.append("Email là bắt buộc.")
        if not password or len(password) < 6:
            errors.append("Mật khẩu phải có ít nhất 6 ký tự.")
        if role not in ["admin", "receptionist", "trainer", "cashier"]:
            errors.append("Vai trò không hợp lệ.")

        if User.query.filter_by(username=username).first():
            errors.append("Tên đăng nhập đã tồn tại.")
        if User.query.filter_by(email=email).first():
            errors.append("Email đã được sử dụng.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("admin/user_create.html")

        user = User(username=username, email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f"Tạo người dùng '{username}' thành công.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_create.html")

@bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_user(id):
    user = User.query.get_or_404(id)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()

        errors = []
        if not username:
            errors.append("Tên đăng nhập là bắt buộc.")
        if not email:
            errors.append("Email là bắt buộc.")
        if role not in ["admin", "receptionist", "trainer", "cashier"]:
            errors.append("Vai trò không hợp lệ.")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != id:
            errors.append("Tên đăng nhập đã tồn tại.")
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != id:
            errors.append("Email đã được sử dụng.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("admin/user_edit.html", user=user)

        user.username = username
        user.email = email
        user.role = role
        
        if password and len(password) >= 6:
            user.set_password(password)
        elif password and len(password) < 6:
            flash("Mật khẩu phải có ít nhất 6 ký tự.", "warning")

        db.session.commit()
        flash(f"Cập nhật người dùng '{username}' thành công.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_edit.html", user=user)

@bp.route("/users/<int:id>/toggle_active", methods=["POST"])
@login_required
def toggle_user_active(id):
    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        flash("Bạn không thể khóa tài khoản của chính mình.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "kích hoạt" if user.is_active else "khóa"
    flash(f"Đã {status} tài khoản '{user.username}'.", "success")
    return redirect(url_for("admin.users"))

@bp.route("/users/<int:id>/delete", methods=["POST"])
@login_required
def delete_user(id):
    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        flash("Bạn không thể xóa tài khoản của chính mình.", "danger")
        return redirect(url_for("admin.users"))

    if user.workout_plans:
        flash("Không thể xóa người dùng có lịch tập liên quan.", "danger")
        return redirect(url_for("admin.users"))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f"Đã xóa người dùng '{username}'.", "success")
    return redirect(url_for("admin.users"))
