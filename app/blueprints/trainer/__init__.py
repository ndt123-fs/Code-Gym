from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Exercise, Member, SystemConfig, WorkoutDetail, WorkoutPlan

bp = Blueprint("trainer", __name__, url_prefix="/trainer")

@bp.route("/dashboard")
@login_required
def dashboard():
    from datetime import date
    
    all_members = Member.query.order_by(Member.full_name).all()
    
    assigned_member_ids = set(
        row[0] for row in db.session.query(WorkoutPlan.member_id)
        .filter_by(trainer_id=current_user.id)
        .distinct()
        .all()
    )
    
    members_data = []
    for member in all_members:
        plan_count = WorkoutPlan.query.filter_by(
            member_id=member.id, 
            trainer_id=current_user.id
        ).count()
        members_data.append({
            "member": member,
            "has_plan": member.id in assigned_member_ids,
            "plan_count": plan_count,
        })
    
    return render_template("trainer/dashboard.html", members_data=members_data, today=date.today())

@bp.route("/view_plans/<int:member_id>")
@login_required
def view_plans(member_id: int):
    member = db.session.get(Member, member_id)
    if not member:
        flash("Không tìm thấy hội viên.", "danger")
        return redirect(url_for("trainer.dashboard"))

    plans = (
        WorkoutPlan.query
        .filter_by(member_id=member_id)
        .order_by(WorkoutPlan.created_at.desc())
        .all()
    )
    return render_template("trainer/view_plans.html", member=member, plans=plans)

@bp.route("/create_plan/<int:member_id>", methods=["GET", "POST"])
@login_required
def create_plan(member_id: int):
    member = db.session.get(Member, member_id)
    if not member:
        flash("Không tìm thấy hội viên.", "danger")
        return redirect(url_for("trainer.dashboard"))

    exercises = Exercise.query.order_by(Exercise.name).all()

    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        exercise_ids = request.form.getlist("exercises[]")
        sets_list = request.form.getlist("sets[]")
        reps_list = request.form.getlist("reps[]")
        schedule_days = request.form.getlist("schedule_days[]")

        errors: list[str] = []
        if not exercise_ids:
            errors.append("Vui lòng thêm ít nhất một bài tập.")

        details: list[WorkoutDetail] = []
        unique_days: set[str] = set()
        
        for exercise_id, sets_value, reps_value, schedule_day in zip(
            exercise_ids, sets_list, reps_list, schedule_days
        ):
            if not exercise_id or not sets_value or not reps_value or not schedule_day:
                errors.append("Vui lòng điền đầy đủ thông tin cho mỗi bài tập.")
                continue

            exercise = db.session.get(Exercise, int(exercise_id)) if exercise_id.isdigit() else None
            if not exercise:
                errors.append("Không tìm thấy bài tập.")
                continue

            try:
                sets_int = int(sets_value)
            except ValueError:
                errors.append("Số hiệp phải là số hợp lệ.")
                continue

            for day in schedule_day.split(","):
                day_normalized = day.strip().lower()
                if day_normalized:
                    unique_days.add(day_normalized)

            details.append(
                WorkoutDetail(
                    exercise=exercise,
                    sets=sets_int,
                    reps=reps_value.strip(),
                    schedule_day=schedule_day.strip(),
                )
            )
        
        max_training_days_str = SystemConfig.get_config("max_training_days", "6")
        try:
            max_training_days = int(max_training_days_str)
        except ValueError:
            max_training_days = 6
        
        if len(unique_days) > max_training_days:
            errors.append(
                f"Lịch tập vượt quá {max_training_days} ngày tập tối đa mỗi tuần. "
                f"Bạn đã chọn {len(unique_days)} ngày."
            )

        if errors or not details:
            if not details and not errors:
                errors.append("Vui lòng thêm ít nhất một bài tập.")
            for message in errors:
                flash(message, "danger")
            return render_template(
                "trainer/create_plan.html",
                member=member,
                exercises=exercises,
            )

        plan = WorkoutPlan(member=member, trainer=current_user, notes=notes)
        db.session.add(plan)
        for detail in details:
            plan.workout_details.append(detail)

        db.session.commit()
        flash("Tạo lịch tập thành công.", "success")
        return redirect(url_for("trainer.dashboard"))

    return render_template("trainer/create_plan.html", member=member, exercises=exercises)
