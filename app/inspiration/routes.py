from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.inspiration import inspiration
from app.models import InspirationItem
from app import db


@inspiration.route("/")
@login_required
def index():
    platform_filter = request.args.get("platform", "")
    query = InspirationItem.query.filter_by(user_id=current_user.id)
    if platform_filter:
        query = query.filter_by(platform=platform_filter)
    items = query.order_by(InspirationItem.created_at.desc()).all()
    return render_template(
        "inspiration/index.html",
        items=items,
        platforms=InspirationItem.PLATFORMS,
        platform_filter=platform_filter,
    )


@inspiration.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = InspirationItem(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()
        flash("Inspiration saved! ✨", "success")
        return redirect(url_for("inspiration.index"))
    return render_template(
        "inspiration/form.html",
        item=None,
        platforms=InspirationItem.PLATFORMS,
        action="New",
    )


@inspiration.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = InspirationItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Inspiration updated!", "success")
        return redirect(url_for("inspiration.index"))
    return render_template(
        "inspiration/form.html",
        item=item,
        platforms=InspirationItem.PLATFORMS,
        action="Edit",
    )


@inspiration.route("/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    item = InspirationItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Inspiration item deleted.", "info")
    return redirect(url_for("inspiration.index"))


def _populate(item, form):
    item.link = form.get("link", "").strip()
    item.platform = form.get("platform", "Website")
    item.category = form.get("category", "").strip()
    item.why_saved = form.get("why_saved", "").strip()
    item.what_learned = form.get("what_learned", "").strip()
    item.action_to_take = form.get("action_to_take", "").strip()
    item.related_profile = form.get("related_profile", "").strip()
