from __future__ import annotations

from datetime import datetime

from dateutil.relativedelta import relativedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message

from app.extensions import db, mail
from app.models import Invoice, Member, Package, User
from app.utils import format_vnd

bp = Blueprint("auth", __name__)

ROLE_REDIRECTS = {
    "receptionist": "/reception/dashboard",
    "trainer": "/trainer/dashboard",
    "cashier": "/cashier/dashboard",
    "admin": "/admin/dashboard",
}

def _redirect_for_role(role: str) -> str:
    return ROLE_REDIRECTS.get(role.lower(), url_for("auth.login"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_redirect_for_role(current_user.role))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên.", "danger")
                return render_template("auth/login.html")
            
            login_user(user)
            flash("Đăng nhập thành công.", "success")
            return redirect(_redirect_for_role(user.role))

        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "danger")

    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("auth.login"))

@bp.route("/register", methods=["GET", "POST"])
def public_register():
    packages = Package.query.order_by(Package.duration_months).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        gender = request.form.get("gender", "").strip()
        dob_raw = request.form.get("dob", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        package_id = request.form.get("package_id", "").strip()

        errors: list[str] = []
        if not full_name:
            errors.append("Họ tên là bắt buộc.")
        if not gender:
            errors.append("Giới tính là bắt buộc.")
        if not dob_raw:
            errors.append("Năm sinh là bắt buộc.")
        if not phone:
            errors.append("Số điện thoại là bắt buộc.")
        if not email:
            errors.append("Email là bắt buộc.")
        if not package_id:
            errors.append("Vui lòng chọn gói tập.")

        try:
            dob = datetime.strptime(dob_raw, "%Y-%m-%d").date() if dob_raw else None
        except ValueError:
            dob = None
            errors.append("Định dạng ngày sinh không hợp lệ.")

        package = db.session.get(Package, int(package_id)) if package_id.isdigit() else None
        if not package:
            errors.append("Gói tập không tồn tại.")

        if Member.query.filter_by(email=email).first():
            errors.append("Email này đã được đăng ký.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("auth/register.html", packages=packages)

        registration_date = datetime.utcnow()
        active_until = (registration_date + relativedelta(months=package.duration_months)).date()

        member = Member(
            full_name=full_name,
            gender=gender,
            dob=dob,
            phone=phone,
            email=email,
            registration_date=registration_date,
            active_until=active_until,
        )
        db.session.add(member)
        db.session.flush()

        invoice = Invoice(
            member_id=member.id,
            package_id=package.id,
            amount=package.price,
        )
        db.session.add(invoice)
        db.session.commit()

        message = Message(
            subject="Xác nhận đăng ký - Code Gym",
            recipients=[member.email],
            body=f"""Xin chào {member.full_name},

Bạn đã đăng ký thành công tại Code Gym!

Thông tin đăng ký:
- Gói tập: {package.name}
- Giá: {format_vnd(package.price)}
- Thời hạn: đến {active_until.strftime('%d/%m/%Y')}

Cảm ơn bạn đã tin tưởng Code Gym!
""",
        )
        try:
            mail.send(message)
            flash(
                f"Đăng ký thành công! Email xác nhận đã được gửi. Số tiền cần thanh toán: {format_vnd(invoice.amount)}",
                "success",
            )
        except Exception:
            flash(
                f"Đăng ký thành công! Số tiền cần thanh toán: {format_vnd(invoice.amount)}. (Email xác nhận không gửi được)",
                "warning",
            )

        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", packages=packages)
