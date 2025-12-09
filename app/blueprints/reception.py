from __future__ import annotations

from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from flask_mail import Message

from app.extensions import db, mail
from app.models import Invoice, Member, Package
from app.utils import format_vnd

bp = Blueprint("reception", __name__, url_prefix="/reception")

@bp.route("/dashboard")
@login_required
def dashboard():
    members = Member.query.order_by(Member.registration_date.desc()).all()
    return render_template("reception/dashboard.html", members=members, today=date.today())

@bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    packages = Package.query.order_by(Package.name).all()

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
            errors.append("Ngày sinh là bắt buộc.")
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
            errors.append("Không tìm thấy gói tập.")

        if Member.query.filter_by(email=email).first():
            errors.append("Email này đã được đăng ký.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("reception/register.html", packages=packages)

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
            body=f"Xin chào {member.full_name}, bạn đã đăng ký gói {package.name}",
        )
        try:
            mail.send(message)
            flash(
                f"Đăng ký hội viên thành công! Email xác nhận đã được gửi. Số tiền: {format_vnd(invoice.amount)}",
                "success",
            )
        except Exception:  # pragma: no cover - mail server issues
            flash(
                f"Đăng ký hội viên thành công! (Email xác nhận không gửi được). Số tiền: {format_vnd(invoice.amount)}",
                "warning",
            )

        return redirect(url_for("reception.dashboard"))

    return render_template("reception/register.html", packages=packages)
