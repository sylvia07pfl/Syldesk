from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.inspiration import inspiration
from app.models import InspirationItem
from app import db
import re
from urllib.parse import urlparse


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


# ---------------------------------------------------------------------------
# Analyze endpoint — returns JSON suggestions for a given URL, no external API
# ---------------------------------------------------------------------------

_PLATFORM_RULES = [
    (r"instagram\.com",   "Instagram"),
    (r"youtube\.com|youtu\.be", "YouTube"),
    (r"linkedin\.com",    "LinkedIn"),
    (r"twitter\.com|x\.com", "Twitter"),
]

_CATEGORY_HINTS = {
    "instagram":  "Personal Branding",
    "youtube":    "Learning Resource",
    "linkedin":   "Professional Networking",
    "twitter":    "Industry Insights",
    "medium":     "Article / Blog",
    "substack":   "Newsletter",
    "coursera":   "Online Course",
    "udemy":      "Online Course",
    "notion":     "Productivity",
    "github":     "Tech / Projects",
    "figma":      "Design",
    "canva":      "Design",
    "hbr":        "Business Strategy",
    "forbes":     "Business Strategy",
    "naukri":     "Job Search",
    "internshala": "Internship",
    "unstop":     "Competitions",
    "youthop":    "Opportunities",
}

_PROFILE_HINTS = {
    "instagram":   "Personal Branding",
    "linkedin":    "HR / Consulting",
    "youtube":     "General Learning",
    "coursera":    "MBA / Consulting",
    "udemy":       "Skill Building",
    "github":      "Tech Portfolio",
    "hbr":         "Consulting",
    "naukri":      "HR",
    "internshala": "Internship",
}

_WHY_TEMPLATES = {
    "Instagram":  "Saved because this Instagram content showcased a real-world career strategy worth studying.",
    "YouTube":    "Saved because this video explains a concept or skill directly relevant to my career goals.",
    "LinkedIn":   "Saved because this post contains professional insight or a networking opportunity worth following up on.",
    "Twitter":    "Saved because this thread shares a timely industry perspective I want to reference later.",
    "Article":    "Saved because this article covers a topic that deepens my understanding of my target domain.",
    "Website":    "Saved because this resource is directly relevant to my current career-building focus.",
}

_LEARNED_TEMPLATES = {
    "Instagram":  "Observed how professionals present their personal brand on social media and what resonates with audiences.",
    "YouTube":    "Gained a structured walkthrough of a skill, framework, or career concept I can apply immediately.",
    "LinkedIn":   "Understood a professional's journey, career move, or strategic insight that I can learn from.",
    "Twitter":    "Captured a concise industry opinion or trend that is shaping the space I want to enter.",
    "Article":    "Absorbed a detailed breakdown of a concept, case study, or best practice in my target area.",
    "Website":    "Discovered a tool, resource, or reference that fills a gap in my current knowledge.",
}

_ACTION_TEMPLATES = {
    "Instagram":  "Follow this creator, study their content strategy, and apply one idea to my own profile this week.",
    "YouTube":    "Watch fully, take notes, and identify one skill or action point to implement within 7 days.",
    "LinkedIn":   "Connect with the author, save their profile, and engage with their next post meaningfully.",
    "Twitter":    "Follow the author, bookmark this thread, and revisit it before my next application round.",
    "Article":    "Read end-to-end, highlight key sections, and add key takeaways to my study notes.",
    "Website":    "Explore the resource thoroughly and determine one actionable step to integrate into my workflow.",
}


def _detect_platform(url: str) -> str:
    for pattern, name in _PLATFORM_RULES:
        if re.search(pattern, url, re.I):
            return name
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    if host.endswith(".com") or host.endswith(".org") or host.endswith(".in"):
        return "Article" if any(k in host for k in ("medium", "substack", "blog", "news", "hbr", "forbes")) else "Website"
    return "Website"


def _extract_handle(url: str, platform: str) -> str:
    """Best-effort extraction of a username/channel from the URL path."""
    try:
        path = urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]
        if not parts:
            return ""
        if platform == "Instagram":
            return f"@{parts[0]}" if parts else ""
        if platform == "YouTube":
            # /channel/UCxxx or /@handle or /c/handle or /user/handle
            if len(parts) >= 2 and parts[0] in ("channel", "c", "user"):
                return parts[1]
            if parts[0].startswith("@"):
                return parts[0]
            return parts[0] if len(parts) == 1 else ""
        if platform == "LinkedIn":
            if len(parts) >= 2 and parts[0] in ("in", "company", "school"):
                return parts[1].replace("-", " ").title()
            return ""
        if platform == "Twitter":
            return f"@{parts[0]}" if parts else ""
    except Exception:
        pass
    return ""


def _category_for(url: str, platform: str) -> str:
    low = url.lower()
    for keyword, cat in _CATEGORY_HINTS.items():
        if keyword in low:
            return cat
    return {
        "Instagram": "Personal Branding",
        "YouTube":   "Learning Resource",
        "LinkedIn":  "Professional Networking",
        "Twitter":   "Industry Insights",
        "Article":   "Article / Blog",
    }.get(platform, "General")


def _related_profile_for(url: str, platform: str) -> str:
    low = url.lower()
    for keyword, profile in _PROFILE_HINTS.items():
        if keyword in low:
            return profile
    return {
        "Instagram": "Personal Branding",
        "LinkedIn":  "HR / Consulting",
        "YouTube":   "General Learning",
    }.get(platform, "General")


@inspiration.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """Return AI-style field suggestions for a pasted URL."""
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    platform = _detect_platform(url)
    handle   = _extract_handle(url, platform)
    category = _category_for(url, platform)
    related  = _related_profile_for(url, platform)

    # Build a short summary line from the URL itself
    parsed = urlparse(url)
    host = parsed.netloc.lstrip("www.")
    path_hint = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
    if handle:
        summary = f"{platform} content from {handle} on {host}."
    elif path_hint:
        label = path_hint.replace("-", " ").replace("_", " ").title()
        summary = f'{platform} resource: "{label}" from {host}.'
    else:
        summary = f"{platform} resource from {host}."

    return jsonify({
        "platform":       platform,
        "category":       category,
        "why_saved":      _WHY_TEMPLATES.get(platform, _WHY_TEMPLATES["Website"]),
        "what_learned":   _LEARNED_TEMPLATES.get(platform, _LEARNED_TEMPLATES["Website"]),
        "action_to_take": _ACTION_TEMPLATES.get(platform, _ACTION_TEMPLATES["Website"]),
        "related_profile": handle or related,
        "summary":        summary,
    })
