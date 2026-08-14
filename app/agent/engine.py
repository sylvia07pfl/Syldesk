"""
Syldesk AI Agent Engine
=======================
Pure-Python, zero external-API intelligence layer.
All logic uses URL structure, domain heuristics, HTML meta-tag
extraction (via stdlib urllib), and rule-based NLP.

Phases covered:
  1 – Zero-friction capture  (analyze_url)
  2 – Autonomous categorisation  (classify)
  3 – Career Agent  (extract_career_data)
  5 – Smart Memory  (build_memory_payload)
"""

from __future__ import annotations

import re
import json
import datetime
from urllib.parse import urlparse, urljoin
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
from typing import Optional

# ---------------------------------------------------------------------------
# PLATFORM DETECTION
# ---------------------------------------------------------------------------

_PLATFORM_MAP = [
    (r"instagram\.com",           "Instagram"),
    (r"threads\.net",             "Threads"),
    (r"youtube\.com|youtu\.be",   "YouTube"),
    (r"linkedin\.com",            "LinkedIn"),
    (r"twitter\.com|x\.com",      "Twitter"),
    (r"reddit\.com",              "Reddit"),
    (r"coursera\.org",            "Course"),
    (r"udemy\.com",               "Course"),
    (r"edx\.org",                 "Course"),
    (r"nptel\.ac\.in",            "Course"),
    (r"swayam\.gov\.in",          "Course"),
    (r"internshala\.com",         "Job Portal"),
    (r"unstop\.com",              "Job Portal"),
    (r"naukri\.com",              "Job Portal"),
    (r"indeed\.com",              "Job Portal"),
    (r"linkedin\.com/jobs",       "Job Portal"),
    (r"youthop\.com",             "Job Portal"),
    (r"letsintern\.com",          "Job Portal"),
    (r"angellist\.com|wellfound\.com", "Job Portal"),
    (r"\.pdf($|\?)",              "PDF"),
    (r"medium\.com|substack\.com|hashnode\.dev|dev\.to|beehiiv\.com", "Article"),
    (r"github\.com",              "Website"),
    (r"notion\.so|notion\.site",  "Website"),
    (r"figma\.com",               "Website"),
]


def detect_platform(url: str) -> str:
    for pattern, name in _PLATFORM_MAP:
        if re.search(pattern, url, re.I):
            return name
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    if any(k in host for k in ("blog", "news", "hbr", "forbes", "inc.", "medium",
                                "substack", "times", "post", "wire")):
        return "Article"
    return "Website"


# ---------------------------------------------------------------------------
# HANDLE / CREATOR EXTRACTION
# ---------------------------------------------------------------------------

def extract_handle(url: str, platform: str) -> str:
    try:
        path = urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]
        if not parts:
            return ""
        if platform == "Instagram":
            # skip /p/, /reel/, /tv/ — those are post paths
            if parts[0] in ("p", "reel", "tv", "stories", "explore"):
                return ""
            return f"@{parts[0]}"
        if platform == "Threads":
            if parts[0].startswith("@"):
                return parts[0]
            return f"@{parts[0]}" if parts else ""
        if platform == "YouTube":
            if len(parts) >= 2 and parts[0] in ("channel", "c", "user"):
                return parts[1]
            if parts[0].startswith("@"):
                return parts[0]
            return ""
        if platform == "LinkedIn":
            if len(parts) >= 2 and parts[0] in ("in", "company", "school"):
                return parts[1].replace("-", " ").title()
            return ""
        if platform == "Twitter":
            skip = {"i", "search", "explore", "notifications", "messages", "home"}
            return f"@{parts[0]}" if parts and parts[0] not in skip else ""
        if platform == "Reddit":
            if len(parts) >= 2 and parts[0] == "r":
                return f"r/{parts[1]}"
            if len(parts) >= 2 and parts[0] == "u":
                return f"u/{parts[1]}"
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# HTML META FETCHER
# ---------------------------------------------------------------------------

class _MetaParser(HTMLParser):
    """Extracts <title>, og:*, twitter:*, description from HTML."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.og: dict = {}
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            prop = d.get("property", "") or d.get("name", "")
            content = d.get("content", "")
            if prop == "og:title":
                self.og["title"] = content
            elif prop == "og:description":
                self.og["description"] = content
            elif prop == "og:site_name":
                self.og["site_name"] = content
            elif prop == "og:type":
                self.og["type"] = content
            elif prop in ("description", "twitter:description"):
                if not self.description:
                    self.description = content
            elif prop == "twitter:title":
                self.og.setdefault("title", content)
            elif prop == "article:author":
                self.og["author"] = content
            elif prop == "article:published_time":
                self.og["published"] = content

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()


def _fetch_meta(url: str, timeout: int = 6) -> dict:
    """Fetch page and extract metadata. Returns empty dict on failure."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            # Only read text/html; skip large binaries
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct and "application/xhtml" not in ct:
                return {}
            raw = resp.read(40_000).decode("utf-8", errors="replace")
        parser = _MetaParser()
        parser.feed(raw)
        return {
            "title":       parser.og.get("title") or parser.title or "",
            "description": parser.og.get("description") or parser.description or "",
            "site_name":   parser.og.get("site_name", ""),
            "og_type":     parser.og.get("type", ""),
            "author":      parser.og.get("author", ""),
            "published":   parser.og.get("published", ""),
        }
    except (URLError, HTTPError, Exception):
        return {}


# ---------------------------------------------------------------------------
# PHASE 2 — CLASSIFICATION ENGINE (30 categories)
# ---------------------------------------------------------------------------

# Keyword → category mapping (ordered by specificity)
_CATEGORY_RULES: list[tuple[list[str], str]] = [
    # Job / Internship portals — checked first
    (["internshala", "letsintern", "youthop", "unstop", "internship",
      "intern ", "summer intern", "winter intern"], "Internship"),
    (["naukri", "indeed", "hiring", "job opening", "full-time", "full time",
      "placement", "job opportunity", "vacancy", "recruitment drive",
      "job description", "apply now", "jd ", " jd,"], "Job Opportunity"),
    (["scholarship", "fellowship", "grant", "stipend opportunity"], "Scholarship"),

    # Learning
    (["coursera", "udemy", "edx", "nptel", "swayam", "online course",
      "certification course", "learn ", "tutorial", "mooc"], "Course"),
    (["cat prep", "cat 2024", "cat 2025", "mba entrance", "xat", "snap",
      "iim", "gmat", "mat exam"], "CAT Preparation"),
    (["mba", "pgdm", "business school", "b-school", "management programme"], "MBA"),

    # Career craft
    (["resume", "cv tips", "cover letter", "ats ", "resume format"], "Resume"),
    (["interview prep", "interview tips", "common interview", "crack interview",
      "hr round", "case interview"], "Interview"),
    (["networking", "linkedin strategy", "cold email", "informational interview",
      "build network"], "Networking"),

    # Business functions
    (["digital marketing", "seo", "sem", "google ads", "meta ads",
      "performance marketing", "email marketing", "content marketing"], "Digital Marketing"),
    (["brand strategy", "brand identity", "brand positioning",
      "brand building", "employer brand"], "Brand Strategy"),
    (["marketing funnel", "marketing strategy", "go-to-market", "gtm",
      "growth hacking", "marketing mix", "4p", "7p"], "Marketing"),
    (["hr ", "human resources", "people ops", "people operations",
      "employee engagement", "onboarding", "hr analytics"], "HR"),
    (["talent acquisition", "sourcing", "headhunting", "recruiter",
      "ats system", "hiring process"], "Recruitment"),
    (["consulting", "consulting case", "mckinsey", "bcg", "bain",
      "deloitte", "pwc", "strategy consulting", "management consulting"], "Consulting"),
    (["product management", "product manager", "prm", "roadmap",
      "user story", "sprint", "agile product"], "Product Management"),
    (["ux design", "ui design", "figma", "wireframe", "user research",
      "usability", "design thinking", "ux/ui"], "UX/UI"),
    (["data analyst", "data science", "sql", "tableau", "power bi",
      "data visualisation", "pandas", "numpy", "excel analytics"], "Data"),
    (["artificial intelligence", "machine learning", "deep learning",
      "llm", "gpt", "neural network", "nlp", "generative ai",
      "diffusion model"], "AI"),
    (["finance", "investment banking", "private equity", "valuation",
      "financial modelling", "cfa", "equity research", "ib "], "Finance"),
    (["business strategy", "porter", "swot", "pestle", "competitive analysis",
      "strategic management", "business model"], "Business Strategy"),
    (["entrepreneurship", "startup", "venture capital", "funding",
      "pitch deck", "founder", "bootstrapping"], "Entrepreneurship"),
    (["research", "white paper", "case study", "academic", "journal",
      "literature review", "phd", "publication"], "Research"),
    (["productivity", "notion", "second brain", "pkm", "time management",
      "deep work", "focus", "pomodoro", "morning routine"], "Productivity"),
    (["personal development", "self improvement", "mindset", "motivation",
      "soft skills", "communication skills", "leadership"], "Personal Development"),

    # Lifestyle
    (["travel", "destination", "itinerary", "visa", "trip planning",
      "backpacking", "solo travel"], "Travel"),
    (["health", "wellness", "mental health", "nutrition", "diet plan",
      "sleep", "meditation"], "Health"),
    (["fitness", "gym", "workout", "exercise", "running", "yoga",
      "weight loss", "strength training"], "Fitness"),
    (["fashion", "outfit", "styling", "ootd", "wardrobe", "clothing haul",
      "fashion week"], "Fashion"),
    (["luxury", "premium brand", "designer", "high-end", "luxury brand",
      "louis vuitton", "gucci", "hermes", "chanel"], "Luxury"),
]


# Domain → category overrides (checked before keyword rules)
_DOMAIN_OVERRIDES = {
    "hbr.org":            "Business Strategy",
    "forbes.com":         "Business Strategy",
    "inc.com":            "Entrepreneurship",
    "harvard.edu":        "Research",
    "mckinsey.com":       "Consulting",
    "bcg.com":            "Consulting",
    "bain.com":           "Consulting",
    "deloitte.com":       "Consulting",
    "pwc.com":            "Consulting",
    "bloomberg.com":      "Finance",
    "ft.com":             "Finance",
    "economist.com":      "Business Strategy",
    "vogue.com":          "Fashion",
    "harpersbazaar.com":  "Fashion",
    "businessoffashion.com": "Luxury",
    "highsnobiety.com":   "Luxury",
    "notion.so":          "Productivity",
    "github.com":         "Research",
    "arxiv.org":          "Research",
    "medium.com":         "Article / Blog",
    "substack.com":       "Article / Blog",
}


def classify(url: str, title: str, description: str, platform: str) -> str:
    """Return the best-matching AI category for the content."""
    # 1. Domain-level override (highest priority)
    from urllib.parse import urlparse as _up
    host = _up(url).netloc.lower().lstrip("www.")
    for domain, cat in _DOMAIN_OVERRIDES.items():
        if domain in host:
            return cat

    haystack = " ".join([url, title, description, platform]).lower()

    # 2. Keyword rules
    for keywords, category in _CATEGORY_RULES:
        for kw in keywords:
            if kw in haystack:
                return category

    # Platform fallbacks
    fallbacks = {
        "Instagram": "Personal Development",
        "YouTube":   "Personal Development",
        "LinkedIn":  "Networking",
        "Twitter":   "Business Strategy",
        "Reddit":    "Research",
        "Course":    "Course",
        "Job Portal": "Job Opportunity",
        "PDF":       "Research",
        "Article":   "Research",
        "Threads":   "Personal Development",
    }
    return fallbacks.get(platform, "Other")


# ---------------------------------------------------------------------------
# AUTO-ROUTING — where should this content live?
# ---------------------------------------------------------------------------

_ROUTE_MAP = {
    "Internship":      "opportunities",
    "Job Opportunity": "opportunities",
    "Scholarship":     "opportunities",
    "Course":          "library",
    "CAT Preparation": "library",
    "MBA":             "library",
    "Research":        "library",
    "Resume":          "library",
    "Interview":       "library",
}


def auto_route(category: str) -> Optional[str]:
    return _ROUTE_MAP.get(category)


# ---------------------------------------------------------------------------
# PHASE 3 — CAREER AGENT
# ---------------------------------------------------------------------------

_SKILL_PATTERNS = [
    r"\bpython\b", r"\bexcel\b", r"\bsql\b", r"\bpowerpoint\b",
    r"\btableau\b", r"\bpower bi\b", r"\bfigma\b", r"\bcanva\b",
    r"\bcontent writing\b", r"\bcopywriting\b", r"\bseo\b",
    r"\bdata analysis\b", r"\bdigital marketing\b", r"\bsocial media\b",
    r"\bproject management\b", r"\bmarket research\b", r"\bcommunication\b",
    r"\bleadership\b", r"\bteamwork\b", r"\bproblem.solving\b",
    r"\bfinancial modelling\b", r"\bvaluation\b", r"\bconsulting\b",
    r"\bagile\b", r"\bscrum\b", r"\bpresentation\b", r"\bpublic speaking\b",
    r"\bai\b", r"\bmachine learning\b", r"\bchatgpt\b",
]

_DEADLINE_PATTERNS = [
    r"deadline[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})",
    r"last date[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})",
    r"apply by[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})",
    r"closes?[:\s]+([a-z]+\s+\d{1,2},?\s+\d{4})",
    r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
]

_STIPEND_PATTERNS = [
    r"(?:stipend|salary|ctc|package)[:\s]*(?:rs\.?|inr|₹)?\s*(\d[\d,.]+\s*(?:k|lpa|per month|pm|lakh)?)",
    r"(?:rs\.?|inr|₹)\s*(\d[\d,.]+\s*(?:k|lpa|per month|pm|lakh)?)",
]

_LOCATION_PATTERNS = [
    r"location[:\s]+([a-z\s,]+?)(?:\n|\.|\|)",
    r"(?:based in|office in|work from)\s+([a-z\s]+?)(?:\n|\.|\|)",
    r"\b(remote|work from home|wfh|hybrid|on.?site)\b",
]


def extract_career_data(url: str, title: str, description: str, platform: str, category: str) -> dict:
    """
    For job/internship content, extract structured career metadata.
    Returns a dict that can populate Opportunity / ApplicationTracker.
    """
    if category not in ("Internship", "Job Opportunity", "Scholarship"):
        return {}

    text = f"{title} {description}".lower()

    # Skills extraction
    skills_found = []
    for pat in _SKILL_PATTERNS:
        if re.search(pat, text, re.I):
            skill = re.sub(r"\\b", "", pat).strip().title()
            skills_found.append(skill)

    # Deadline extraction
    deadline_raw = ""
    for pat in _DEADLINE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            deadline_raw = m.group(1)
            break

    # Stipend extraction
    stipend = ""
    for pat in _STIPEND_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            stipend = m.group(0)
            break

    # Location extraction
    location = "Not specified"
    for pat in _LOCATION_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            location = m.group(1).strip().title()
            break

    # Domain / company from URL
    parsed = urlparse(url)
    host = parsed.netloc.lstrip("www.").split(".")[0].title()

    # Priority scoring
    high_value_signals = ["dream", "top", "mnc", "fortune 500", "google",
                          "amazon", "meta", "microsoft", "mckinsey", "bcg"]
    priority = "High" if any(s in text for s in high_value_signals) else "Medium"

    # Application checklist
    checklist = [
        "Update resume for this role",
        "Write a tailored cover letter",
        "Research the company/organization",
        "Identify 2-3 talking points from your experience",
        "Apply before the deadline",
        "Set a follow-up reminder",
    ]
    if skills_found:
        checklist.insert(2, f"Highlight skills: {', '.join(skills_found[:4])}")

    # Recommendation
    is_recommended = len(skills_found) >= 2 or priority == "High"
    recommendation = (
        "Strong match — apply this week" if is_recommended
        else "Good to explore — check requirements before applying"
    )

    return {
        "company":       host,
        "role":          _extract_role(title),
        "location":      location,
        "stipend":       stipend or "Not specified",
        "deadline_raw":  deadline_raw,
        "skills_required": skills_found[:8],
        "priority":      priority,
        "checklist":     checklist,
        "recommendation": recommendation,
        "domain":        category,
        "source":        platform,
    }


def _extract_role(title: str) -> str:
    """Heuristically extract the role name from a page title."""
    # "Marketing Intern | Company" → "Marketing Intern"
    for sep in ["|", "–", "—", "-", " at ", " @"]:
        if sep in title:
            parts = title.split(sep)
            # Take the part that looks like a role (shorter, often first)
            candidate = parts[0].strip()
            if 3 < len(candidate) < 80:
                return candidate
    return title[:80] if title else "Unknown Role"


# ---------------------------------------------------------------------------
# PHASE 5 — SMART MEMORY / SEMANTIC SEARCH HELPERS
# ---------------------------------------------------------------------------

def build_memory_payload(url: str, meta: dict, platform: str, category: str,
                         handle: str, career: dict) -> dict:
    """
    Assemble the full Smart Memory payload for an InspirationItem.
    """
    title       = meta.get("title", "")
    description = meta.get("description", "")
    site_name   = meta.get("site_name", "")
    og_type     = meta.get("og_type", "")

    # Content type inference
    content_type_map = {
        "video":   "Video",
        "article": "Article",
        "website": "Website",
        "profile": "Profile",
        "book":    "Book",
    }
    content_type = content_type_map.get(og_type.lower(), _infer_content_type(url, platform))

    # Domain (broad field)
    domain = _infer_domain(category)

    # Tags (union of category keywords + platform)
    tags = _generate_tags(url, title, description, category, platform)

    # Keywords (from title + description noun phrases)
    keywords = _generate_keywords(title, description)

    # Urgency + value
    urgency, opp_value = _score_urgency_value(category, career)

    # Career relevance
    career_rel = "High" if category in (
        "Internship", "Job Opportunity", "Scholarship", "Resume",
        "Interview", "Consulting", "HR", "Marketing", "MBA", "Networking"
    ) else "Medium" if category in (
        "Course", "Digital Marketing", "Brand Strategy", "Product Management",
        "Data", "AI", "Recruitment", "Finance", "Business Strategy"
    ) else "Low"

    # Confidence score (0–1): based on how much metadata we got
    score = 0.0
    if title:         score += 0.3
    if description:   score += 0.2
    if handle:        score += 0.15
    if career:        score += 0.2
    if tags:          score += 0.15
    score = round(min(score, 1.0), 2)

    # Summaries
    summary = _build_summary(title, description, platform, category, handle, site_name)
    detailed = _build_detailed_summary(title, description, category, career, tags)

    # Revisit date
    revisit = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()

    # Why saved / learned / action — now platform+category aware
    why_saved      = _why_saved(platform, category, title)
    what_learned   = _what_learned(platform, category, title)
    action_to_take = _action_to_take(category, career)

    return {
        "platform":         platform,
        "category":         category,
        "title":            title,
        "summary":          summary,
        "detailed_summary": detailed,
        "domain":           domain,
        "topic":            category,
        "career_function":  _career_function(category),
        "content_type":     content_type,
        "creator":          handle or meta.get("author", ""),
        "company":          career.get("company", "") or site_name,
        "tags":             ", ".join(tags[:12]),
        "keywords":         ", ".join(keywords[:10]),
        "is_actionable":    bool(career) or category in ("Internship", "Job Opportunity", "Scholarship"),
        "urgency":          urgency,
        "opportunity_value": opp_value,
        "career_relevance": career_rel,
        "confidence_score": score,
        "revisit_date":     revisit,
        "priority":         career.get("priority", "Medium"),
        "related_skill":    ", ".join(career.get("skills_required", [])[:3]),
        "why_saved":        why_saved,
        "what_learned":     what_learned,
        "action_to_take":   action_to_take,
        "related_profile":  handle,
        "ai_analyzed":      True,
        "auto_route_target": auto_route(category) or "",
        "is_auto_routed":   bool(auto_route(category)),
        # Career agent extras (returned separately in API but also stored)
        "_career":          career,
    }


# ── Internal helpers ────────────────────────────────────────────────────────

def _infer_content_type(url: str, platform: str) -> str:
    path = urlparse(url).path.lower()
    if "/reel/" in path or "/shorts/" in path:   return "Reel"
    if "/watch" in path or "youtu.be" in url:    return "Video"
    if "/post/" in path or "/p/" in path:        return "Post"
    if "/jobs/" in path or "/internship" in path: return "Job Listing"
    if ".pdf" in path:                           return "PDF"
    if "/course/" in path or "/learn/" in path:  return "Course"
    if "/article/" in path or "/blog/" in path:  return "Article"
    return {"Instagram": "Post", "YouTube": "Video", "LinkedIn": "Post",
            "Twitter": "Thread", "Reddit": "Thread", "Job Portal": "Job Listing",
            "Course": "Course", "PDF": "PDF", "Article": "Article"}.get(platform, "Web Page")


def _infer_domain(category: str) -> str:
    _domain_map = {
        "Marketing": "Business", "Brand Strategy": "Business",
        "Digital Marketing": "Business", "Consulting": "Business",
        "Product Management": "Business", "Business Strategy": "Business",
        "Finance": "Finance", "MBA": "Business", "Entrepreneurship": "Business",
        "HR": "Human Resources", "Recruitment": "Human Resources",
        "Talent Acquisition": "Human Resources",
        "Data": "Technology", "AI": "Technology", "Machine Learning": "Technology",
        "UX/UI": "Technology",
        "Resume": "Career", "Interview": "Career", "Networking": "Career",
        "Internship": "Career", "Job Opportunity": "Career",
        "Scholarship": "Career", "CAT Preparation": "Career",
        "Course": "Learning", "Research": "Learning",
        "Productivity": "Self", "Personal Development": "Self",
        "Health": "Lifestyle", "Fitness": "Lifestyle", "Travel": "Lifestyle",
        "Fashion": "Lifestyle", "Luxury": "Lifestyle",
    }
    return _domain_map.get(category, "General")


def _career_function(category: str) -> str:
    _func_map = {
        "Marketing": "Marketing", "Digital Marketing": "Marketing",
        "Brand Strategy": "Marketing", "HR": "HR", "Recruitment": "HR",
        "Talent Acquisition": "HR", "Finance": "Finance",
        "Consulting": "Consulting", "Product Management": "Product",
        "Data": "Data & Analytics", "AI": "AI / Tech",
        "Machine Learning": "AI / Tech", "UX/UI": "Design",
        "Internship": "Career Building", "Job Opportunity": "Career Building",
    }
    return _func_map.get(category, "General")


def _generate_tags(url: str, title: str, description: str, category: str, platform: str) -> list[str]:
    tags = [category, platform]
    haystack = f"{title} {description} {url}".lower()

    tag_signals = {
        "internship": "Internship", "job": "Job", "remote": "Remote",
        "free course": "Free Course", "certification": "Certification",
        "case study": "Case Study", "resume": "Resume Tips",
        "networking": "Networking", "linkedin": "LinkedIn",
        "ai": "AI", "python": "Python", "excel": "Excel",
        "canva": "Canva", "figma": "Figma", "notion": "Notion",
        "startup": "Startup", "mba": "MBA", "consulting": "Consulting",
        "marketing": "Marketing", "data": "Data", "branding": "Branding",
        "design": "Design", "finance": "Finance", "hr": "HR",
        "interview": "Interview Tips", "salary": "Salary Insights",
    }
    for signal, tag in tag_signals.items():
        if signal in haystack and tag not in tags:
            tags.append(tag)
    return list(dict.fromkeys(tags))  # deduplicate, preserve order


def _generate_keywords(title: str, description: str) -> list[str]:
    text = f"{title} {description}"
    # Extract capitalized phrases and significant tokens
    words = re.findall(r"\b[A-Z][a-z]{2,}\b|\b[A-Z]{2,}\b", text)
    # Also grab lowercase meaningful tokens (len > 4, not stopwords)
    _stop = {"with", "that", "this", "from", "have", "will", "your", "about",
             "learn", "make", "more", "best", "into", "when", "been", "their",
             "them", "they", "some", "what", "which", "would", "could", "should"}
    lower_words = [w for w in re.findall(r"\b[a-z]{5,}\b", text.lower())
                   if w not in _stop]
    combined = words + lower_words
    # Deduplicate case-insensitively
    seen, result = set(), []
    for w in combined:
        key = w.lower()
        if key not in seen:
            seen.add(key)
            result.append(w)
    return result[:10]


def _score_urgency_value(category: str, career: dict) -> tuple[str, str]:
    urgent_cats = {"Internship", "Job Opportunity", "Scholarship"}
    high_value  = {"Internship", "Job Opportunity", "Scholarship", "Consulting",
                   "MBA", "Networking", "Resume", "Interview"}

    urgency = "High" if category in urgent_cats else "Medium" if category in (
        "Course", "Networking", "Resume", "Interview") else "Low"

    if career.get("priority") == "High":
        urgency = "High"

    opp_value = "High" if category in high_value else "Medium" if category in (
        "Digital Marketing", "Brand Strategy", "Marketing", "Data", "AI",
        "Product Management", "HR", "Finance") else "Low"

    return urgency, opp_value


def _build_summary(title, description, platform, category, handle, site_name) -> str:
    who = handle or site_name
    who_part = f" by {who}" if who else ""
    if title:
        return f'{title}{who_part} — {category} content from {platform}.'
    if description:
        return description[:160] + ("…" if len(description) > 160 else "")
    return f"{category} content from {platform}."


def _build_detailed_summary(title, description, category, career, tags) -> str:
    parts = []
    if title:
        parts.append(f"**{title}**")
    if description:
        parts.append(description[:300])
    if career.get("role"):
        parts.append(f"Role: {career['role']}")
    if career.get("company"):
        parts.append(f"Organization: {career['company']}")
    if career.get("location"):
        parts.append(f"Location: {career['location']}")
    if career.get("stipend") and career["stipend"] != "Not specified":
        parts.append(f"Compensation: {career['stipend']}")
    if career.get("skills_required"):
        parts.append(f"Key skills: {', '.join(career['skills_required'][:5])}")
    if career.get("recommendation"):
        parts.append(f"💡 {career['recommendation']}")
    if not parts:
        return f"Saved {category} content for future reference."
    return "\n".join(parts)


# ── Contextual text generators ──────────────────────────────────────────────

_WHY = {
    "Internship":       "Saved to explore this internship opportunity — checking eligibility and fit.",
    "Job Opportunity":  "Saved as a potential job opportunity worth researching and applying to.",
    "Scholarship":      "Saved this scholarship to evaluate eligibility and prepare an application.",
    "Course":           "Saved to add this course to my learning roadmap.",
    "Resume":           "Saved for resume tips and strategies to apply to my CV immediately.",
    "Interview":        "Saved interview prep material to review before my next application round.",
    "Networking":       "Saved to follow up on a networking opportunity or study a professional's journey.",
    "Marketing":        "Saved for marketing strategy insights relevant to my career focus.",
    "Consulting":       "Saved consulting content to deepen my case-prep and strategy knowledge.",
    "HR":               "Saved HR content to build domain knowledge for my target profile.",
    "AI":               "Saved AI content to stay current with the field and find skill gaps.",
    "Instagram":        "Saved this Instagram content — a creative idea or career inspiration worth revisiting.",
    "YouTube":          "Saved this video for an in-depth learning session.",
    "LinkedIn":         "Saved this LinkedIn post for professional insight or networking follow-up.",
    "Productivity":     "Saved to improve my systems and daily workflow.",
    "Personal Development": "Saved for mindset, soft skills, or career clarity.",
    "Fashion":          "Saved for style or branding inspiration.",
    "Luxury":           "Saved for luxury market research or brand strategy study.",
}

_LEARNED = {
    "Internship":       "Understood the role requirements, skills needed, and what the organization looks for.",
    "Job Opportunity":  "Gained clarity on the role scope, required experience, and application process.",
    "Scholarship":      "Learned the eligibility criteria, deadlines, and what a strong application looks like.",
    "Course":           "Identified a structured learning path for a new skill or knowledge area.",
    "Resume":           "Picked up a specific resume strategy, format tip, or ATS optimization technique.",
    "Interview":        "Captured a framework, common question, or preparation strategy for interviews.",
    "Networking":       "Observed a professional's path or networking strategy I can model.",
    "Marketing":        "Absorbed a marketing concept, campaign insight, or strategic framework.",
    "Consulting":       "Studied a consulting framework, case study, or problem-solving approach.",
    "AI":               "Stayed updated on an AI trend, tool, or concept relevant to my work.",
    "Instagram":        "Observed what content style, personal brand approach, or creative idea resonates.",
    "YouTube":          "Gained a walkthrough of a concept, skill, or career strategy.",
    "LinkedIn":         "Absorbed professional insight from someone I admire or want to learn from.",
}

_ACTION = {
    "Internship":       "Complete the application checklist, update my resume, and apply before the deadline.",
    "Job Opportunity":  "Research the company, tailor my resume, write a cover letter, and apply.",
    "Scholarship":      "Check eligibility, gather required documents, and submit before the deadline.",
    "Course":           "Enroll or bookmark, schedule dedicated study time, and complete with notes.",
    "Resume":           "Apply one specific tip to my resume this week and save the improved version.",
    "Interview":        "Practice answers to questions in this content before my next interview.",
    "Networking":       "Connect with the author or profile, and send a genuine message within 48 hours.",
    "AI":               "Experiment with the tool or concept in a small personal project this week.",
    "Instagram":        "Follow the creator, study their strategy, and apply one idea to my own profile.",
    "YouTube":          "Watch fully, take structured notes, and identify one immediate action point.",
    "LinkedIn":         "Connect with the author and engage meaningfully with their next post.",
    "Marketing":        "Apply one marketing insight to a current project or case study.",
    "Consulting":       "Practise the framework with a real case and add it to my case-prep notes.",
    "Productivity":     "Implement one productivity system change this week and track results.",
}


def _why_saved(platform: str, category: str, title: str) -> str:
    return _WHY.get(category) or _WHY.get(platform) or (
        f"Saved because this content about {category.lower()} is relevant to my current goals."
    )


def _what_learned(platform: str, category: str, title: str) -> str:
    return _LEARNED.get(category) or _LEARNED.get(platform) or (
        f"Gained insight into {category.lower()} that I can apply to my career journey."
    )


def _action_to_take(category: str, career: dict) -> str:
    if career.get("checklist"):
        return career["checklist"][0]  # top checklist item as the primary action
    return _ACTION.get(category) or "Review this saved item and decide on a concrete next step."


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def analyze_url(url: str) -> dict:
    """
    Master entry point for the AI Agent.
    Returns the full payload to populate all InspirationItem fields.
    """
    platform = detect_platform(url)
    handle   = extract_handle(url, platform)
    meta     = _fetch_meta(url)           # may be empty for locked platforms
    title    = meta.get("title", "")
    desc     = meta.get("description", "")
    category = classify(url, title, desc, platform)
    career   = extract_career_data(url, title, desc, platform, category)
    payload  = build_memory_payload(url, meta, platform, category, handle, career)

    return payload
