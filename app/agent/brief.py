"""
Syldesk Daily Brief Agent — Phase 6
=====================================
Generates a structured daily career brief from the database.
No external API — pure data aggregation + pattern recognition.
"""
from __future__ import annotations
from datetime import date, timedelta
from app.models import (
    InspirationItem, Opportunity, ApplicationTracker,
    SkillRoadmap, Project, Notification, StudyMaterial
)
from app import db


def generate_daily_brief(user_id: int) -> dict:
    today      = date.today()
    week_ago   = today - timedelta(days=7)
    week_ahead = today + timedelta(days=7)

    # ── New opportunities (saved in last 24h)
    new_opportunities = Opportunity.query.filter(
        Opportunity.user_id == user_id,
        Opportunity.created_at >= db.func.datetime('now', '-1 day'),
        Opportunity.is_archived == False,
    ).order_by(Opportunity.created_at.desc()).limit(5).all()

    # ── Expiring deadlines
    expiring = Opportunity.query.filter(
        Opportunity.user_id == user_id,
        Opportunity.deadline != None,
        Opportunity.deadline >= today,
        Opportunity.deadline <= week_ahead,
        Opportunity.is_archived == False,
    ).order_by(Opportunity.deadline.asc()).limit(5).all()

    # ── Active applications
    active_apps = ApplicationTracker.query.filter(
        ApplicationTracker.user_id == user_id,
        ApplicationTracker.status.in_(["Applied", "Shortlisted", "Interview Scheduled"]),
    ).order_by(ApplicationTracker.created_at.desc()).limit(5).all()

    # ── High urgency inspirations
    urgent_inspirations = InspirationItem.query.filter_by(
        user_id=user_id, urgency="High", is_actionable=True
    ).order_by(InspirationItem.created_at.desc()).limit(5).all()

    # ── Revisit due
    revisit_due = InspirationItem.query.filter(
        InspirationItem.user_id == user_id,
        InspirationItem.revisit_date != None,
        InspirationItem.revisit_date <= today,
    ).order_by(InspirationItem.revisit_date.asc()).limit(5).all()

    # ── Skills needing attention (< 50% progress)
    lagging_skills = SkillRoadmap.query.filter(
        SkillRoadmap.user_id == user_id,
        SkillRoadmap.progress_percent < 50,
    ).order_by(SkillRoadmap.progress_percent.asc()).limit(4).all()

    # ── Pattern detection: what categories are being saved most this week?
    recent_items = InspirationItem.query.filter(
        InspirationItem.user_id == user_id,
        InspirationItem.created_at >= db.func.datetime('now', '-7 days'),
    ).all()

    category_counts: dict[str, int] = {}
    for item in recent_items:
        cat = item.category or "Other"
        category_counts[cat] = category_counts.get(cat, 0) + 1
    top_categories = sorted(category_counts.items(), key=lambda x: -x[1])[:3]

    # ── Forgotten opportunities (saved > 14 days ago, still "Saved" status)
    forgotten = Opportunity.query.filter(
        Opportunity.user_id == user_id,
        Opportunity.status == "Saved",
        Opportunity.created_at <= db.func.datetime('now', '-14 days'),
        Opportunity.is_archived == False,
    ).order_by(Opportunity.created_at.asc()).limit(4).all()

    # ── Weekly stats
    week_inspirations = InspirationItem.query.filter(
        InspirationItem.user_id == user_id,
        InspirationItem.created_at >= db.func.datetime('now', '-7 days'),
    ).count()

    week_opportunities = Opportunity.query.filter(
        Opportunity.user_id == user_id,
        Opportunity.created_at >= db.func.datetime('now', '-7 days'),
    ).count()

    # ── Suggested next actions (smart priority queue)
    next_actions = _build_next_actions(
        expiring, urgent_inspirations, lagging_skills, active_apps, revisit_due
    )

    return {
        "date":               today.isoformat(),
        "new_opportunities":  new_opportunities,
        "expiring":           expiring,
        "active_apps":        active_apps,
        "urgent_inspirations": urgent_inspirations,
        "revisit_due":        revisit_due,
        "lagging_skills":     lagging_skills,
        "top_categories":     top_categories,
        "forgotten":          forgotten,
        "week_inspirations":  week_inspirations,
        "week_opportunities": week_opportunities,
        "next_actions":       next_actions,
    }


def _build_next_actions(expiring, urgent, lagging_skills, active_apps, revisit_due) -> list[dict]:
    actions = []

    for opp in expiring[:2]:
        days_left = (opp.deadline - date.today()).days
        actions.append({
            "icon": "🔥",
            "priority": "High",
            "text": f'Apply to "{opp.title}" — {days_left} day{"s" if days_left != 1 else ""} left',
            "link": "/opportunities/",
        })

    for item in urgent[:2]:
        actions.append({
            "icon": "🎯",
            "priority": "High",
            "text": f'Action needed: {item.action_to_take or item.title or "Review this item"}',
            "link": "/inspiration/inbox",
        })

    for app in active_apps[:1]:
        actions.append({
            "icon": "📋",
            "priority": "Medium",
            "text": f'Follow up on {app.company} ({app.status})',
            "link": "/applications/",
        })

    for skill in lagging_skills[:1]:
        actions.append({
            "icon": "📚",
            "priority": "Medium",
            "text": f'Study time for "{skill.title}" — {skill.progress_percent}% done',
            "link": "/skills/",
        })

    for item in revisit_due[:1]:
        actions.append({
            "icon": "🔁",
            "priority": "Low",
            "text": f'Revisit: {item.title or item.link}',
            "link": "/inspiration/inbox",
        })

    return actions[:6]  # Max 6 actions
