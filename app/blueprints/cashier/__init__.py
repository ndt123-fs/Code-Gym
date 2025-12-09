from __future__ import annotations

import calendar
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Invoice, Member, Package

bp = Blueprint("cashier", __name__, url_prefix="/cashier")

@bp.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("cashier.payment"))

def _add_months(start_date: date, months: int) -> date:
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

@bp.route("/payment", methods=["GET", "POST"])
@login_required
def payment():
    members = Member.query.order_by(Member.full_name).all()
    packages = Package.query.order_by(Package.duration_months).all()

    if request.method == "POST":
        member_id = request.form.get("member_id", "").strip()
        package_id = request.form.get("package_id", "").strip()

        errors: list[str] = []
        member = db.session.get(Member, int(member_id)) if member_id.isdigit() else None
        if not member:
            errors.append("Không tìm thấy hội viên.")

        package = db.session.get(Package, int(package_id)) if package_id.isdigit() else None
        if not package:
            errors.append("Không tìm thấy gói tập.")

        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template(
                "cashier/payment.html", members=members, packages=packages
            )

        invoice = Invoice(member=member, package=package, amount=package.price)
        db.session.add(invoice)

        today = date.today()
        base_date = (
            member.active_until if member.active_until and member.active_until >= today else today
        )
        member.active_until = _add_months(base_date, package.duration_months)

        db.session.commit()
        flash("Thanh toán thành công và đã cập nhật thời hạn hội viên.", "success")
        return redirect(url_for("cashier.payment"))

    return render_template("cashier/payment.html", members=members, packages=packages)

@bp.route("/history", methods=["GET"])
@login_required
def history():
    members = Member.query.order_by(Member.full_name).all()
    
    member_id = request.args.get("member_id", "").strip()
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    
    query = Invoice.query
    
    if member_id and member_id.isdigit():
        query = query.filter(Invoice.member_id == int(member_id))
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            query = query.filter(Invoice.created_at >= start_date)
        except ValueError:
            flash("Định dạng ngày bắt đầu không hợp lệ", "danger")
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            query = query.filter(Invoice.created_at <= end_date)
        except ValueError:
            flash("Định dạng ngày kết thúc không hợp lệ", "danger")
    
    invoices = query.order_by(Invoice.created_at.desc()).all()
    
    current_year = datetime.utcnow().year
    monthly_totals = [0.0] * 12
    
    revenue_results = (
        db.session.query(
            db.func.extract("month", Invoice.created_at).label("month"),
            db.func.sum(Invoice.amount).label("total"),
        )
        .filter(db.func.extract("year", Invoice.created_at) == current_year)
        .group_by("month")
        .order_by("month")
        .all()
    )
    
    for row in revenue_results:
        month_index = int(row.month) - 1
        monthly_totals[month_index] = float(row.total)
    
    monthly_labels = ["Th1", "Th2", "Th3", "Th4", "Th5", "Th6", 
                      "Th7", "Th8", "Th9", "Th10", "Th11", "Th12"]
    
    total_revenue = sum(monthly_totals)
    
    return render_template(
        "cashier/history.html",
        invoices=invoices,
        members=members,
        selected_member_id=member_id,
        start_date=start_date_str,
        end_date=end_date_str,
        monthly_labels=monthly_labels,
        monthly_data=monthly_totals,
        total_revenue=total_revenue,
        current_year=current_year,
    )
