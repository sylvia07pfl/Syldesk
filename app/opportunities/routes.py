from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.opportunities import opportunities
from app.models import Opportunity
from app import db
from datetime import datetime


@opportunities.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "")
    category_filter = request.args.get("category", "")
    priority_filter = request.args.get("priority", "")
    show_archived = request.args.get("archived", "false") == "true"

    query = Opportunity.query.filter_by(user_id=current_user.id, is_archived=show_archived)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)

    items = query.order_by(Opportunity.is_pinned.desc(), Opportunity.created_at.desc()).all()
    return render_template(
        "opportunities/index.html",
        items=items,
        categories=Opportunity.CATEGORIES,
        priorities=Opportunity.PRIORITIES,
        statuses=Opportunity.STATUSES,
        status_filter=status_filter,
        category_filter=category_filter,
        priority_filter=priority_filter,
        show_archived=show_archived,
    )


@opportunities.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        opp = Opportunity(user_id=current_user.id)
        _populate_opportunity(opp, request.form)
        db.session.add(opp)
        db.session.commit()
        flash("Opportunity saved! 🌸", "success")
        return redirect(url_for("opportunities.index"))
    return render_template(
        "opportunities/form.html",
        item=None,
        categories=Opportunity.CATEGORIES,
        priorities=Opportunity.PRIORITIES,
        statuses=Opportunity.STATUSES,
        action="New",
    )


@opportunities.route("/<int:opp_id>/edit", methods=["GET", "POST"])
@login_required
def edit(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate_opportunity(opp, request.form)
        db.session.commit()
        flash("Opportunity updated! ✨", "success")
        return redirect(url_for("opportunities.index"))
    return render_template(
        "opportunities/form.html",
        item=opp,
        categories=Opportunity.CATEGORIES,
        priorities=Opportunity.PRIORITIES,
        statuses=Opportunity.STATUSES,
        action="Edit",
    )


@opportunities.route("/<int:opp_id>/delete", methods=["POST"])
@login_required
def delete(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, user_id=current_user.id).first_or_404()
    db.session.delete(opp)
    db.session.commit()
    flash("Opportunity deleted.", "info")
    return redirect(url_for("opportunities.index"))


@opportunities.route("/<int:opp_id>/toggle-pin", methods=["POST"])
@login_required
def toggle_pin(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, user_id=current_user.id).first_or_404()
    opp.is_pinned = not opp.is_pinned
    db.session.commit()
    return redirect(request.referrer or url_for("opportunities.index"))


@opportunities.route("/<int:opp_id>/toggle-star", methods=["POST"])
@login_required
def toggle_star(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, user_id=current_user.id).first_or_404()
    opp.is_starred = not opp.is_starred
    db.session.commit()
    return redirect(request.referrer or url_for("opportunities.index"))


@opportunities.route("/<int:opp_id>/toggle-archive", methods=["POST"])
@login_required
def toggle_archive(opp_id):
    opp = Opportunity.query.filter_by(id=opp_id, user_id=current_user.id).first_or_404()
    opp.is_archived = not opp.is_archived
    db.session.commit()
    flash("Opportunity archived." if opp.is_archived else "Opportunity restored.", "info")
    return redirect(request.referrer or url_for("opportunities.index"))


def _populate_opportunity(opp, form):
    opp.title = form.get("title", "").strip()
    opp.company = form.get("company", "").strip()
    opp.link = form.get("link", "").strip()
    opp.source = form.get("source", "").strip()
    opp.category = form.get("category", "Internship")
    opp.priority = form.get("priority", "Medium")
    opp.status = form.get("status", "Saved")
    opp.notes = form.get("notes", "").strip()
    opp.is_pinned = bool(form.get("is_pinned"))
    opp.is_starred = bool(form.get("is_starred"))
    deadline_str = form.get("deadline", "")
    applied_str = form.get("applied_date", "")
    opp.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date() if deadline_str else None
    opp.applied_date = datetime.strptime(applied_str, "%Y-%m-%d").date() if applied_str else None
