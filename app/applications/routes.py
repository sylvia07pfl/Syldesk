from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.applications import applications
from app.models import ApplicationTracker
from app import db
from datetime import datetime


@applications.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "")
    query = ApplicationTracker.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(ApplicationTracker.created_at.desc()).all()
    return render_template(
        "applications/index.html",
        items=items,
        statuses=ApplicationTracker.STATUSES,
        status_filter=status_filter,
    )


@applications.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = ApplicationTracker(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Application tracked! 📋", "success")
        return redirect(url_for("applications.index"))
    return render_template(
        "applications/form.html",
        item=None,
        statuses=ApplicationTracker.STATUSES,
        action="New",
    )


@applications.route("/<int:app_id>/edit", methods=["GET", "POST"])
@login_required
def edit(app_id):
    item = ApplicationTracker.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Application updated! ✨", "success")
        return redirect(url_for("applications.index"))
    return render_template(
        "applications/form.html",
        item=item,
        statuses=ApplicationTracker.STATUSES,
        action="Edit",
    )


@applications.route("/<int:app_id>/delete", methods=["POST"])
@login_required
def delete(app_id):
    item = ApplicationTracker.query.filter_by(id=app_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Application entry deleted.", "info")
    return redirect(url_for("applications.index"))


def _populate(item, form):
    item.company = form.get("company", "").strip()
    item.role = form.get("role", "").strip()
    item.status = form.get("status", "Saved")
    item.result = form.get("result", "").strip()
    item.notes = form.get("notes", "").strip()

    def _parse_date(key):
        val = form.get(key, "")
        return datetime.strptime(val, "%Y-%m-%d").date() if val else None

    item.applied_date = _parse_date("applied_date")
    item.deadline = _parse_date("deadline")
    item.interview_date = _parse_date("interview_date")
    item.follow_up_reminder = _parse_date("follow_up_reminder")
