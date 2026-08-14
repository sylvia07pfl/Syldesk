from datetime import date, timedelta
from flask import render_template
from flask_login import login_required, current_user
from app.dashboard import dashboard
from app.models import (
    Opportunity, ApplicationTracker, Project,
    SkillRoadmap, BackupPlan, Notification
)


@dashboard.route("/")
@login_required
def index():
    today = date.today()
    week_ahead = today + timedelta(days=7)

    # Summary counts
    total_opportunities = Opportunity.query.filter_by(
        user_id=current_user.id, is_archived=False
    ).count()
    active_applications = ApplicationTracker.query.filter(
        ApplicationTracker.user_id == current_user.id,
        ApplicationTracker.status.in_(["Applied", "Shortlisted", "Interview Scheduled", "Interview Completed"])
    ).count()
    total_projects = Project.query.filter_by(
        user_id=current_user.id, is_archived=False
    ).count()
    total_roadmaps = SkillRoadmap.query.filter_by(user_id=current_user.id).count()

    # Upcoming deadlines — opportunities
    upcoming_opps = Opportunity.query.filter(
        Opportunity.user_id == current_user.id,
        Opportunity.deadline >= today,
        Opportunity.deadline <= week_ahead,
        Opportunity.is_archived == False
    ).order_by(Opportunity.deadline.asc()).limit(5).all()

    # Upcoming deadlines — applications
    upcoming_apps = ApplicationTracker.query.filter(
        ApplicationTracker.user_id == current_user.id,
        ApplicationTracker.deadline >= today,
        ApplicationTracker.deadline <= week_ahead
    ).order_by(ApplicationTracker.deadline.asc()).limit(5).all()

    # Pinned / starred items
    pinned_opps = Opportunity.query.filter_by(
        user_id=current_user.id, is_pinned=True, is_archived=False
    ).order_by(Opportunity.created_at.desc()).limit(4).all()

    pinned_projects = Project.query.filter_by(
        user_id=current_user.id, is_pinned=True, is_archived=False
    ).order_by(Project.created_at.desc()).limit(4).all()

    # Recent activity (last 5 of each major model)
    recent_opps = Opportunity.query.filter_by(
        user_id=current_user.id
    ).order_by(Opportunity.created_at.desc()).limit(5).all()

    recent_projects = Project.query.filter_by(
        user_id=current_user.id
    ).order_by(Project.created_at.desc()).limit(5).all()

    # Unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()
    unread_count = len(unread_notifications)

    # Skill progress (average)
    roadmaps = SkillRoadmap.query.filter_by(user_id=current_user.id).all()
    avg_skill_progress = 0
    if roadmaps:
        avg_skill_progress = round(sum(r.progress_percent or 0 for r in roadmaps) / len(roadmaps))

    # Backup plans
    active_backup = BackupPlan.query.filter(
        BackupPlan.user_id == current_user.id,
        BackupPlan.status.in_(["Not Started", "In Progress"])
    ).count()

    return render_template(
        "dashboard/index.html",
        today=today,
        total_opportunities=total_opportunities,
        active_applications=active_applications,
        total_projects=total_projects,
        total_roadmaps=total_roadmaps,
        upcoming_opps=upcoming_opps,
        upcoming_apps=upcoming_apps,
        pinned_opps=pinned_opps,
        pinned_projects=pinned_projects,
        recent_opps=recent_opps,
        recent_projects=recent_projects,
        unread_notifications=unread_notifications,
        unread_count=unread_count,
        avg_skill_progress=avg_skill_progress,
        active_backup=active_backup,
    )
