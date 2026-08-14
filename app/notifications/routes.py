from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.notifications import notifications
from app.models import Notification
from app import db


@notifications.route("/")
@login_required
def index():
    items = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    return render_template("notifications/index.html", items=items)


@notifications.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for("notifications.index"))


@notifications.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(request.referrer or url_for("notifications.index"))


@notifications.route("/<int:notif_id>/delete", methods=["POST"])
@login_required
def delete(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    db.session.delete(notif)
    db.session.commit()
    return redirect(request.referrer or url_for("notifications.index"))
