from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.projects import projects
from app.models import Project
from app import db
from datetime import datetime


@projects.route("/")
@login_required
def index():
    domain_filter = request.args.get("domain", "")
    status_filter = request.args.get("status", "")
    show_archived = request.args.get("archived", "false") == "true"
    query = Project.query.filter_by(user_id=current_user.id, is_archived=show_archived)
    if domain_filter:
        query = query.filter_by(domain=domain_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    items = query.order_by(Project.is_pinned.desc(), Project.created_at.desc()).all()
    return render_template(
        "projects/index.html",
        items=items,
        domains=Project.DOMAINS,
        statuses=Project.STATUSES,
        priorities=Project.PRIORITIES,
        domain_filter=domain_filter,
        status_filter=status_filter,
        show_archived=show_archived,
    )


@projects.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = Project(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Project created! 🚀", "success")
        return redirect(url_for("projects.index"))
    return render_template(
        "projects/form.html",
        item=None,
        domains=Project.DOMAINS,
        statuses=Project.STATUSES,
        priorities=Project.PRIORITIES,
        action="New",
    )


@projects.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    item = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Project updated! ✨", "success")
        return redirect(url_for("projects.index"))
    return render_template(
        "projects/form.html",
        item=item,
        domains=Project.DOMAINS,
        statuses=Project.STATUSES,
        priorities=Project.PRIORITIES,
        action="Edit",
    )


@projects.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id):
    item = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("projects.index"))


@projects.route("/<int:project_id>/toggle-pin", methods=["POST"])
@login_required
def toggle_pin(project_id):
    item = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    item.is_pinned = not item.is_pinned
    db.session.commit()
    return redirect(request.referrer or url_for("projects.index"))


@projects.route("/<int:project_id>/toggle-archive", methods=["POST"])
@login_required
def toggle_archive(project_id):
    item = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    item.is_archived = not item.is_archived
    db.session.commit()
    flash("Project archived." if item.is_archived else "Project restored.", "info")
    return redirect(request.referrer or url_for("projects.index"))


def _populate(item, form):
    item.title = form.get("title", "").strip()
    item.domain = form.get("domain", "Personal")
    item.sub_category = form.get("sub_category", "").strip()
    item.github_link = form.get("github_link", "").strip()
    item.demo_link = form.get("demo_link", "").strip()
    item.description = form.get("description", "").strip()
    item.skills_used = form.get("skills_used", "").strip()
    item.status = form.get("status", "Planning")
    item.priority = form.get("priority", "Medium")
    item.notes = form.get("notes", "").strip()
    item.is_pinned = bool(form.get("is_pinned"))
    item.is_starred = bool(form.get("is_starred"))

    def _parse_date(key):
        val = form.get(key, "")
        return datetime.strptime(val, "%Y-%m-%d").date() if val else None

    item.date_started = _parse_date("date_started")
    item.date_completed = _parse_date("date_completed")
