from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.library import library
from app.models import StudyMaterial
from app import db


@library.route("/")
@login_required
def index():
    category_filter = request.args.get("category", "")
    type_filter = request.args.get("material_type", "")
    query = StudyMaterial.query.filter_by(user_id=current_user.id)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if type_filter:
        query = query.filter_by(material_type=type_filter)
    items = query.order_by(StudyMaterial.created_at.desc()).all()
    return render_template(
        "library/index.html",
        items=items,
        categories=StudyMaterial.CATEGORIES,
        material_types=StudyMaterial.MATERIAL_TYPES,
        category_filter=category_filter,
        type_filter=type_filter,
    )


@library.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = StudyMaterial(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Study material added! 📖", "success")
        return redirect(url_for("library.index"))
    return render_template(
        "library/form.html",
        item=None,
        categories=StudyMaterial.CATEGORIES,
        material_types=StudyMaterial.MATERIAL_TYPES,
        action="New",
    )


@library.route("/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
def edit(material_id):
    item = StudyMaterial.query.filter_by(id=material_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Material updated! ✨", "success")
        return redirect(url_for("library.index"))
    return render_template(
        "library/form.html",
        item=item,
        categories=StudyMaterial.CATEGORIES,
        material_types=StudyMaterial.MATERIAL_TYPES,
        action="Edit",
    )


@library.route("/<int:material_id>/delete", methods=["POST"])
@login_required
def delete(material_id):
    item = StudyMaterial.query.filter_by(id=material_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Material deleted.", "info")
    return redirect(url_for("library.index"))


def _populate(item, form):
    item.title = form.get("title", "").strip()
    item.category = form.get("category", "")
    item.material_type = form.get("material_type", "")
    item.link = form.get("link", "").strip()
    item.notes = form.get("notes", "").strip()
    item.tags = form.get("tags", "").strip()
