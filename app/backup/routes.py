from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.backup import backup
from app.models import BackupPlan
from app import db
from datetime import datetime


@backup.route("/")
@login_required
def index():
    category_filter = request.args.get("category", "")
    status_filter = request.args.get("status", "")
    query = BackupPlan.query.filter_by(user_id=current_user.id)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(BackupPlan.created_at.desc()).all()
    return render_template(
        "backup/index.html",
        items=items,
        categories=BackupPlan.CATEGORIES,
        statuses=BackupPlan.STATUSES,
        priorities=BackupPlan.PRIORITIES,
        category_filter=category_filter,
        status_filter=status_filter,
    )


@backup.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = BackupPlan(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Backup plan added! 🛡️", "success")
        return redirect(url_for("backup.index"))
    return render_template(
        "backup/form.html",
        item=None,
        categories=BackupPlan.CATEGORIES,
        statuses=BackupPlan.STATUSES,
        priorities=BackupPlan.PRIORITIES,
        action="New",
    )


@backup.route("/<int:plan_id>/edit", methods=["GET", "POST"])
@login_required
def edit(plan_id):
    item = BackupPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Backup plan updated! ✨", "success")
        return redirect(url_for("backup.index"))
    return render_template(
        "backup/form.html",
        item=item,
        categories=BackupPlan.CATEGORIES,
        statuses=BackupPlan.STATUSES,
        priorities=BackupPlan.PRIORITIES,
        action="Edit",
    )


@backup.route("/<int:plan_id>/delete", methods=["POST"])
@login_required
def delete(plan_id):
    item = BackupPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Backup plan deleted.", "info")
    return redirect(url_for("backup.index"))


def _populate(item, form):
    item.title = form.get("title", "").strip()
    item.category = form.get("category", "Other")
    item.description = form.get("description", "").strip()
    item.status = form.get("status", "Not Started")
    item.priority = form.get("priority", "Medium")
    item.notes = form.get("notes", "").strip()
    deadline_str = form.get("deadline", "")
    item.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date() if deadline_str else None
