from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.profiles import profiles
from app.models import Profile
from app import db
import json


@profiles.route("/")
@login_required
def index():
    items = Profile.query.filter_by(user_id=current_user.id).order_by(Profile.updated_at.desc()).all()
    return render_template(
        "profiles/index.html",
        items=items,
        profile_types=Profile.PROFILE_TYPES,
    )


@profiles.route("/<int:profile_id>")
@login_required
def detail(profile_id):
    item = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    return render_template("profiles/detail.html", item=item)


@profiles.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = Profile(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Profile created! 🌸", "success")
        return redirect(url_for("profiles.index"))
    return render_template(
        "profiles/detail.html",
        item=None,
        profile_types=Profile.PROFILE_TYPES,
        action="New",
    )


@profiles.route("/<int:profile_id>/edit", methods=["GET", "POST"])
@login_required
def edit(profile_id):
    item = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Profile updated! ✨", "success")
        return redirect(url_for("profiles.detail", profile_id=item.id))
    return render_template(
        "profiles/detail.html",
        item=item,
        profile_types=Profile.PROFILE_TYPES,
        action="Edit",
    )


@profiles.route("/<int:profile_id>/delete", methods=["POST"])
@login_required
def delete(profile_id):
    item = Profile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Profile deleted.", "info")
    return redirect(url_for("profiles.index"))


def _populate(item, form):
    item.profile_type = form.get("profile_type", "HR")
    item.resume_notes = form.get("resume_notes", "").strip()
    item.portfolio_notes = form.get("portfolio_notes", "").strip()
    item.cover_letter_template = form.get("cover_letter_template", "").strip()
    item.profile_score = int(form.get("profile_score", 0) or 0)
    checklist_raw = form.get("skills_checklist", "")
    try:
        item.skills_checklist = json.loads(checklist_raw) if checklist_raw else {}
    except (ValueError, TypeError):
        item.skills_checklist = {}
