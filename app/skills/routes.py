from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.skills import skills
from app.models import SkillRoadmap, SkillItem
from app import db
from datetime import datetime
import json


@skills.route("/")
@login_required
def index():
    roadmaps = SkillRoadmap.query.filter_by(user_id=current_user.id).order_by(SkillRoadmap.created_at.desc()).all()
    return render_template("skills/index.html", roadmaps=roadmaps)


@skills.route("/<int:roadmap_id>")
@login_required
def detail(roadmap_id):
    roadmap = SkillRoadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first_or_404()
    skill_items = SkillItem.query.filter_by(roadmap_id=roadmap_id).order_by(SkillItem.id.asc()).all()
    return render_template("skills/detail.html", roadmap=roadmap, skill_items=skill_items)


@skills.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        roadmap = SkillRoadmap(user_id=current_user.id)
        _populate_roadmap(roadmap, request.form)
        db.session.add(roadmap)
        db.session.commit()
        flash("Skill roadmap created! 📚", "success")
        return redirect(url_for("skills.detail", roadmap_id=roadmap.id))
    return render_template("skills/detail.html", roadmap=None, skill_items=[], action="New")


@skills.route("/<int:roadmap_id>/edit", methods=["GET", "POST"])
@login_required
def edit(roadmap_id):
    roadmap = SkillRoadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first_or_404()
    skill_items = SkillItem.query.filter_by(roadmap_id=roadmap_id).all()
    if request.method == "POST":
        _populate_roadmap(roadmap, request.form)
        db.session.commit()
        flash("Roadmap updated! ✨", "success")
        return redirect(url_for("skills.detail", roadmap_id=roadmap.id))
    return render_template("skills/detail.html", roadmap=roadmap, skill_items=skill_items, action="Edit")


@skills.route("/<int:roadmap_id>/add-skill", methods=["POST"])
@login_required
def add_skill(roadmap_id):
    SkillRoadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first_or_404()
    skill = SkillItem(roadmap_id=roadmap_id)
    skill.skill_name = request.form.get("skill_name", "").strip()
    skill.resources = request.form.get("resources", "").strip()
    skill.notes = request.form.get("notes", "").strip()
    skill.progress_percent = int(request.form.get("progress_percent", 0) or 0)
    last_studied_str = request.form.get("last_studied", "")
    skill.last_studied = datetime.strptime(last_studied_str, "%Y-%m-%d").date() if last_studied_str else None
    skill.is_completed = skill.progress_percent == 100
    db.session.add(skill)
    db.session.commit()
    _recalculate_roadmap_progress(roadmap_id)
    flash("Skill added!", "success")
    return redirect(url_for("skills.detail", roadmap_id=roadmap_id))


@skills.route("/<int:roadmap_id>/delete-skill/<int:skill_id>", methods=["POST"])
@login_required
def delete_skill(roadmap_id, skill_id):
    SkillRoadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first_or_404()
    skill = SkillItem.query.filter_by(id=skill_id, roadmap_id=roadmap_id).first_or_404()
    db.session.delete(skill)
    db.session.commit()
    _recalculate_roadmap_progress(roadmap_id)
    flash("Skill removed.", "info")
    return redirect(url_for("skills.detail", roadmap_id=roadmap_id))


@skills.route("/<int:roadmap_id>/delete", methods=["POST"])
@login_required
def delete(roadmap_id):
    roadmap = SkillRoadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first_or_404()
    db.session.delete(roadmap)
    db.session.commit()
    flash("Roadmap deleted.", "info")
    return redirect(url_for("skills.index"))


def _populate_roadmap(roadmap, form):
    roadmap.title = form.get("title", "").strip()
    roadmap.target_role = form.get("target_role", "").strip()
    roadmap.notes = form.get("notes", "").strip()
    required_raw = form.get("required_skills", "")
    try:
        roadmap.required_skills = json.loads(required_raw) if required_raw else []
    except (ValueError, TypeError):
        roadmap.required_skills = []


def _recalculate_roadmap_progress(roadmap_id):
    items = SkillItem.query.filter_by(roadmap_id=roadmap_id).all()
    if items:
        avg = round(sum(s.progress_percent or 0 for s in items) / len(items))
    else:
        avg = 0
    roadmap = SkillRoadmap.query.get(roadmap_id)
    if roadmap:
        roadmap.progress_percent = avg
        db.session.commit()
