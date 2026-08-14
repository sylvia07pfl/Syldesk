"""
Inspiration module routes — Agentic edition
============================================
Phases 1-3, 5, 7 wired together here.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.inspiration import inspiration
from app.models import InspirationItem, Notification, Opportunity, StudyMaterial
from app import db
from app.agent.engine import analyze_url, auto_route


# ---------------------------------------------------------------------------
# INDEX  — with smart filters and semantic search
# ---------------------------------------------------------------------------

@inspiration.route("/")
@login_required
def index():
    platform_filter  = request.args.get("platform", "")
    category_filter  = request.args.get("category", "")
    domain_filter    = request.args.get("domain", "")
    urgency_filter   = request.args.get("urgency", "")
    search_q         = request.args.get("q", "").strip()

    query = InspirationItem.query.filter_by(user_id=current_user.id)

    if platform_filter:
        query = query.filter_by(platform=platform_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if domain_filter:
        query = query.filter_by(domain=domain_filter)
    if urgency_filter:
        query = query.filter_by(urgency=urgency_filter)
    if search_q:
        like = f"%{search_q}%"
        query = query.filter(
            db.or_(
                InspirationItem.title.ilike(like),
                InspirationItem.summary.ilike(like),
                InspirationItem.category.ilike(like),
                InspirationItem.tags.ilike(like),
                InspirationItem.keywords.ilike(like),
                InspirationItem.creator.ilike(like),
                InspirationItem.company.ilike(like),
                InspirationItem.why_saved.ilike(like),
                InspirationItem.what_learned.ilike(like),
                InspirationItem.domain.ilike(like),
                InspirationItem.link.ilike(like),
            )
        )

    items = query.order_by(InspirationItem.created_at.desc()).all()

    # Sidebar counts for smart collections
    total       = InspirationItem.query.filter_by(user_id=current_user.id).count()
    actionable  = InspirationItem.query.filter_by(user_id=current_user.id, is_actionable=True).count()
    high_urgency = InspirationItem.query.filter_by(user_id=current_user.id, urgency="High").count()
    auto_routed  = InspirationItem.query.filter_by(user_id=current_user.id, is_auto_routed=True).count()
    ai_analyzed  = InspirationItem.query.filter_by(user_id=current_user.id, ai_analyzed=True).count()

    return render_template(
        "inspiration/index.html",
        items=items,
        platforms=InspirationItem.PLATFORMS,
        categories=InspirationItem.AI_CATEGORIES,
        platform_filter=platform_filter,
        category_filter=category_filter,
        domain_filter=domain_filter,
        urgency_filter=urgency_filter,
        search_q=search_q,
        total=total,
        actionable=actionable,
        high_urgency=high_urgency,
        auto_routed=auto_routed,
        ai_analyzed=ai_analyzed,
    )


# ---------------------------------------------------------------------------
# NEW / EDIT / DELETE
# ---------------------------------------------------------------------------

@inspiration.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        item = InspirationItem(user_id=current_user.id)
        _populate(item, request.form)
        db.session.add(item)
        db.session.commit()

        # Phase 7 — auto-route side effects after save
        _run_post_save_agent(item)

        flash("Inspiration saved! ✨", "success")
        return redirect(url_for("inspiration.index"))

    return render_template(
        "inspiration/form.html",
        item=None,
        platforms=InspirationItem.PLATFORMS,
        categories=InspirationItem.AI_CATEGORIES,
        action="New",
    )


@inspiration.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit(item_id):
    item = InspirationItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        _populate(item, request.form)
        db.session.commit()
        flash("Inspiration updated! ✨", "success")
        return redirect(url_for("inspiration.index"))
    return render_template(
        "inspiration/form.html",
        item=item,
        platforms=InspirationItem.PLATFORMS,
        categories=InspirationItem.AI_CATEGORIES,
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


# ---------------------------------------------------------------------------
# Phase 4 — SHARE TARGET  (Android PWA share intent receiver)
# ---------------------------------------------------------------------------

@inspiration.route("/share", methods=["GET", "POST"])
@login_required
def share_target():
    """
    Receives content shared from Android share sheet (PWA Web Share Target).
    GET:  ?url=...&title=...&text=...  (from share sheet)
    POST: form body with url / title / text
    """
    if request.method == "POST":
        url   = (request.form.get("url") or "").strip()
        title = (request.form.get("title") or "").strip()
        text  = (request.form.get("text") or "").strip()
    else:
        url   = (request.args.get("url") or "").strip()
        title = (request.args.get("title") or "").strip()
        text  = (request.args.get("text") or "").strip()

    # Extract a URL from the text field if url is empty (Instagram shares text+url)
    if not url and text:
        m = re.search(r"https?://[^\s]+", text)
        if m:
            url = m.group(0)

    if not url:
        flash("No URL received from share. Please paste it manually.", "warning")
        return redirect(url_for("inspiration.new"))

    # Auto-analyze
    try:
        payload = analyze_url(url)
    except Exception:
        payload = {}

    # Pre-fill a new item and show the form for confirmation
    item = InspirationItem(
        user_id=current_user.id,
        link=url,
        title=title or payload.get("title", ""),
        platform=payload.get("platform", "Website"),
        category=payload.get("category", ""),
        summary=payload.get("summary", ""),
        why_saved=payload.get("why_saved", ""),
        what_learned=payload.get("what_learned", ""),
        action_to_take=payload.get("action_to_take", ""),
        related_profile=payload.get("related_profile", ""),
        tags=payload.get("tags", ""),
        keywords=payload.get("keywords", ""),
        creator=payload.get("creator", ""),
        is_actionable=payload.get("is_actionable", False),
        urgency=payload.get("urgency", "Low"),
        career_relevance=payload.get("career_relevance", "Medium"),
        confidence_score=payload.get("confidence_score", 0.0),
        ai_analyzed=payload.get("ai_analyzed", False),
    )
    db.session.add(item)
    db.session.commit()
    _run_post_save_agent(item)

    flash(f"Shared link captured and analyzed! ✨ Platform: {item.platform}", "success")
    return redirect(url_for("inspiration.edit", item_id=item.id))


# ---------------------------------------------------------------------------
# Phase 1 — ANALYZE ENDPOINT  (rich JSON, all 8-phase metadata)
# ---------------------------------------------------------------------------

@inspiration.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """
    Full AI analysis of a URL. Returns JSON with all Smart Memory fields.
    No external API — pure heuristics + HTML meta extraction.
    """
    data = request.get_json(silent=True) or {}
    url  = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        payload = analyze_url(url)
    except Exception as exc:
        return jsonify({"error": f"Analysis failed: {exc}"}), 500

    # Remove internal key before sending to client
    payload.pop("_career", None)

    return jsonify(payload)


# ---------------------------------------------------------------------------
# Phase 5 — SEMANTIC SEARCH  (keyword + field-aware)
# ---------------------------------------------------------------------------

@inspiration.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%{q}%"
        results = InspirationItem.query.filter(
            InspirationItem.user_id == current_user.id,
            db.or_(
                InspirationItem.title.ilike(like),
                InspirationItem.summary.ilike(like),
                InspirationItem.tags.ilike(like),
                InspirationItem.keywords.ilike(like),
                InspirationItem.category.ilike(like),
                InspirationItem.creator.ilike(like),
                InspirationItem.company.ilike(like),
                InspirationItem.domain.ilike(like),
                InspirationItem.why_saved.ilike(like),
                InspirationItem.what_learned.ilike(like),
            )
        ).order_by(InspirationItem.created_at.desc()).limit(30).all()

    return render_template(
        "inspiration/search.html",
        results=results,
        q=q,
    )


# ---------------------------------------------------------------------------
# Phase 6 — AI INBOX  (items needing review: actionable, high urgency)
# ---------------------------------------------------------------------------

@inspiration.route("/inbox")
@login_required
def inbox():
    """AI Inbox — surface the most important saved items today."""
    today = date.today()

    high_urgency = InspirationItem.query.filter_by(
        user_id=current_user.id, urgency="High", is_actionable=True
    ).order_by(InspirationItem.created_at.desc()).limit(10).all()

    revisit_due = InspirationItem.query.filter(
        InspirationItem.user_id == current_user.id,
        InspirationItem.revisit_date != None,
        InspirationItem.revisit_date <= today,
    ).order_by(InspirationItem.revisit_date.asc()).limit(10).all()

    career_items = InspirationItem.query.filter(
        InspirationItem.user_id == current_user.id,
        InspirationItem.career_relevance == "High",
    ).order_by(InspirationItem.created_at.desc()).limit(8).all()

    recent_unanalyzed = InspirationItem.query.filter_by(
        user_id=current_user.id, ai_analyzed=False
    ).order_by(InspirationItem.created_at.desc()).limit(5).all()

    return render_template(
        "inspiration/inbox.html",
        high_urgency=high_urgency,
        revisit_due=revisit_due,
        career_items=career_items,
        recent_unanalyzed=recent_unanalyzed,
        today=today,
    )


# ---------------------------------------------------------------------------
# Phase 7 — AGENT ACTIVITY  (auto-routed items log)
# ---------------------------------------------------------------------------

@inspiration.route("/agent-feed")
@login_required
def agent_feed():
    routed = InspirationItem.query.filter(
        InspirationItem.user_id == current_user.id,
        InspirationItem.is_auto_routed == True,
    ).order_by(InspirationItem.created_at.desc()).limit(30).all()

    recent_ai = InspirationItem.query.filter_by(
        user_id=current_user.id, ai_analyzed=True
    ).order_by(InspirationItem.created_at.desc()).limit(20).all()

    return render_template(
        "inspiration/agent_feed.html",
        routed=routed,
        recent_ai=recent_ai,
    )


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _populate(item: InspirationItem, form) -> None:
    """Populate all InspirationItem fields from a form submission."""
    # Core original fields
    item.link            = form.get("link", "").strip()
    item.platform        = form.get("platform", "Website")
    item.category        = form.get("category", "").strip()
    item.why_saved       = form.get("why_saved", "").strip()
    item.what_learned    = form.get("what_learned", "").strip()
    item.action_to_take  = form.get("action_to_take", "").strip()
    item.related_profile = form.get("related_profile", "").strip()

    # Phase 5 Smart Memory fields
    item.title              = form.get("title", "").strip()
    item.summary            = form.get("summary", "").strip()
    item.detailed_summary   = form.get("detailed_summary", "").strip()
    item.domain             = form.get("domain", "").strip()
    item.topic              = form.get("topic", "").strip()
    item.career_function    = form.get("career_function", "").strip()
    item.content_type       = form.get("content_type", "").strip()
    item.creator            = form.get("creator", "").strip()
    item.company            = form.get("company", "").strip()
    item.tags               = form.get("tags", "").strip()
    item.keywords           = form.get("keywords", "").strip()
    item.related_skill      = form.get("related_skill", "").strip()
    item.urgency            = form.get("urgency", "Low")
    item.opportunity_value  = form.get("opportunity_value", "Low")
    item.career_relevance   = form.get("career_relevance", "Medium")
    item.priority           = form.get("priority", "Medium")
    item.is_actionable      = form.get("is_actionable") == "on"

    # Confidence score (from hidden field set by JS after analyze)
    try:
        item.confidence_score = float(form.get("confidence_score", 0) or 0)
    except (ValueError, TypeError):
        item.confidence_score = 0.0

    # ai_analyzed flag
    if form.get("ai_analyzed") == "1":
        item.ai_analyzed = True

    # Revisit date
    revisit_raw = form.get("revisit_date", "").strip()
    if revisit_raw:
        try:
            item.revisit_date = date.fromisoformat(revisit_raw)
        except ValueError:
            pass


def _run_post_save_agent(item: InspirationItem) -> None:
    """
    Phase 7 — synchronous post-save agent actions.
    Runs after an item is committed so item.id is available.
    Performs auto-routing and creates Notifications.
    """
    route = auto_route(item.category or "")
    if not route:
        return

    item.is_auto_routed   = True
    item.auto_route_target = route

    if route == "opportunities" and item.category in ("Internship", "Job Opportunity", "Scholarship"):
        # Create or find an Opportunity record
        existing = Opportunity.query.filter_by(
            user_id=item.user_id,
            link=item.link,
        ).first()
        if not existing:
            opp = Opportunity(
                user_id=item.user_id,
                title=item.title or item.category,
                company=item.company or "",
                link=item.link,
                source=item.platform,
                category=_map_opp_category(item.category),
                priority=item.priority or "Medium",
                status="Saved",
                notes=(item.summary or "") + (
                    f"\n\nAuto-captured from Inspiration. Tags: {item.tags}" if item.tags else ""
                ),
            )
            db.session.add(opp)

        # Notification
        notif = Notification(
            user_id=item.user_id,
            title=f"🎯 New {item.category} detected",
            message=f'"{item.title or item.link}" was auto-added to your Opportunities.',
            notification_type="success",
            related_model="InspirationItem",
            related_id=item.id,
        )
        db.session.add(notif)

    elif route == "library":
        existing = StudyMaterial.query.filter_by(
            user_id=item.user_id,
            link=item.link,
        ).first()
        if not existing:
            mat = StudyMaterial(
                user_id=item.user_id,
                title=item.title or item.category,
                category=_map_study_category(item.category),
                material_type=_map_material_type(item.platform),
                link=item.link,
                notes=item.summary or "",
                tags=item.tags or "",
            )
            db.session.add(mat)

        notif = Notification(
            user_id=item.user_id,
            title=f"📚 Added to Library",
            message=f'"{item.title or item.link}" was auto-added to your Study Library.',
            notification_type="info",
            related_model="InspirationItem",
            related_id=item.id,
        )
        db.session.add(notif)

    db.session.commit()


def _map_opp_category(cat: str) -> str:
    return {"Internship": "Internship", "Job Opportunity": "Job",
            "Scholarship": "Scholarship"}.get(cat, "Internship")


def _map_study_category(cat: str) -> str:
    return {"Course": "AI", "CAT Preparation": "CAT", "MBA": "MBA",
            "Resume": "Resume", "Interview": "HR",
            "Research": "Consulting"}.get(cat, "HR")


def _map_material_type(platform: str) -> str:
    return {"YouTube": "YouTube", "PDF": "PDF", "Article": "Website",
            "Course": "Website", "Website": "Website"}.get(platform, "Website")
