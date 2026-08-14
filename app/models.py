from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    opportunities = db.relationship("Opportunity", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    inspiration_items = db.relationship("InspirationItem", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    profiles = db.relationship("Profile", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    skill_roadmaps = db.relationship("SkillRoadmap", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    application_trackers = db.relationship("ApplicationTracker", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    study_materials = db.relationship("StudyMaterial", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    backup_plans = db.relationship("BackupPlan", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    projects = db.relationship("Project", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    agent_jobs = db.relationship("AgentJob", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Opportunity(db.Model):
    __tablename__ = "opportunities"

    CATEGORIES = ["Internship", "Job", "Fellowship", "Workshop", "Webinar", "Competition", "Course", "Scholarship"]
    PRIORITIES = ["High", "Medium", "Low"]
    STATUSES = ["Saved", "Applied", "Shortlisted", "Rejected", "Expired"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    link = db.Column(db.Text)
    source = db.Column(db.String(120))
    category = db.Column(db.String(50), default="Internship")
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(30), default="Saved")
    deadline = db.Column(db.Date)
    applied_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    is_pinned = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Opportunity {self.title}>"


class InspirationItem(db.Model):
    __tablename__ = "inspiration_items"

    PLATFORMS = ["Instagram", "YouTube", "LinkedIn", "Twitter", "Threads",
                 "Reddit", "Website", "Article", "PDF", "Course", "Job Portal"]

    AI_CATEGORIES = [
        "Marketing", "Brand Strategy", "Digital Marketing",
        "HR", "Recruitment", "Talent Acquisition",
        "Finance", "Consulting", "Product Management", "UX/UI",
        "Data", "AI", "Machine Learning", "Business Strategy",
        "MBA", "CAT Preparation", "Internship", "Job Opportunity",
        "Scholarship", "Course", "Networking", "Resume", "Interview",
        "Productivity", "Personal Development", "Travel", "Health",
        "Fitness", "Fashion", "Luxury", "Entrepreneurship",
        "Research", "Other",
    ]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Core fields (existing)
    link = db.Column(db.Text)
    platform = db.Column(db.String(50), default="Website")
    category = db.Column(db.String(120))
    why_saved = db.Column(db.Text)
    what_learned = db.Column(db.Text)
    action_to_take = db.Column(db.Text)
    related_profile = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Phase 5 — Smart Memory fields (new, all nullable for migration safety)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)
    detailed_summary = db.Column(db.Text)
    domain = db.Column(db.String(120))
    topic = db.Column(db.String(120))
    career_function = db.Column(db.String(120))
    content_type = db.Column(db.String(50))       # reel / article / course / job / etc.
    creator = db.Column(db.String(255))
    company = db.Column(db.String(255))
    tags = db.Column(db.Text)                      # comma-separated
    keywords = db.Column(db.Text)                  # comma-separated
    is_actionable = db.Column(db.Boolean, default=False)
    urgency = db.Column(db.String(20), default="Low")          # High / Medium / Low
    opportunity_value = db.Column(db.String(20), default="Low")
    career_relevance = db.Column(db.String(20), default="Medium")
    confidence_score = db.Column(db.Float, default=0.0)
    revisit_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default="Medium")
    is_auto_routed = db.Column(db.Boolean, default=False)      # was moved to another module?
    auto_route_target = db.Column(db.String(50))               # opportunities / library / etc.
    related_skill = db.Column(db.String(120))
    ai_analyzed = db.Column(db.Boolean, default=False)

    def tags_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def keywords_list(self):
        return [k.strip() for k in (self.keywords or "").split(",") if k.strip()]

    def __repr__(self):
        return f"<InspirationItem {self.id}>"


class AgentJob(db.Model):
    """Tracks background agent processing jobs."""
    __tablename__ = "agent_jobs"

    STATUSES = ["queued", "running", "done", "failed"]
    JOB_TYPES = ["analyze_link", "career_agent", "daily_brief", "smart_tag"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="queued")
    payload = db.Column(db.JSON)
    result = db.Column(db.JSON)
    error_msg = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<AgentJob {self.job_type} {self.status}>"


class Profile(db.Model):
    __tablename__ = "profiles"

    PROFILE_TYPES = ["HR", "Marketing", "Consulting", "MBA", "Backup"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    profile_type = db.Column(db.String(50), nullable=False)
    resume_notes = db.Column(db.Text)
    portfolio_notes = db.Column(db.Text)
    cover_letter_template = db.Column(db.Text)
    skills_checklist = db.Column(db.JSON)
    profile_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Profile {self.profile_type}>"


class SkillRoadmap(db.Model):
    __tablename__ = "skill_roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    target_role = db.Column(db.String(120))
    required_skills = db.Column(db.JSON)
    progress_percent = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skill_items = db.relationship("SkillItem", backref="roadmap", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SkillRoadmap {self.title}>"


class SkillItem(db.Model):
    __tablename__ = "skill_items"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("skill_roadmaps.id"), nullable=False)
    skill_name = db.Column(db.String(120), nullable=False)
    resources = db.Column(db.Text)
    progress_percent = db.Column(db.Integer, default=0)
    last_studied = db.Column(db.Date)
    notes = db.Column(db.Text)
    is_completed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<SkillItem {self.skill_name}>"


class ApplicationTracker(db.Model):
    __tablename__ = "application_trackers"

    STATUSES = [
        "Saved", "Applied", "Shortlisted",
        "Interview Scheduled", "Interview Completed",
        "Rejected", "Offer Received"
    ]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255))
    applied_date = db.Column(db.Date)
    deadline = db.Column(db.Date)
    interview_date = db.Column(db.Date)
    result = db.Column(db.String(120))
    status = db.Column(db.String(50), default="Saved")
    follow_up_reminder = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ApplicationTracker {self.company} - {self.role}>"


class StudyMaterial(db.Model):
    __tablename__ = "study_materials"

    CATEGORIES = ["CAT", "HR", "Marketing", "Consulting", "AI", "Excel", "Communication", "Resume", "MBA"]
    MATERIAL_TYPES = ["PDF", "Document", "Note", "YouTube", "Website"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50))
    material_type = db.Column(db.String(30))
    link = db.Column(db.Text)
    notes = db.Column(db.Text)
    tags = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StudyMaterial {self.title}>"


class BackupPlan(db.Model):
    __tablename__ = "backup_plans"

    CATEGORIES = ["Government", "SSC", "Banking", "Entrance", "Certification", "Skill", "Other"]
    STATUSES = ["Not Started", "In Progress", "Completed", "On Hold"]
    PRIORITIES = ["High", "Medium", "Low"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="Not Started")
    priority = db.Column(db.String(20), default="Medium")
    deadline = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BackupPlan {self.title}>"


class Project(db.Model):
    __tablename__ = "projects"

    DOMAINS = ["AI", "Marketing", "HR", "Consulting", "Personal", "Data", "Business"]
    STATUSES = ["Planning", "In Progress", "Completed", "On Hold"]
    PRIORITIES = ["High", "Medium", "Low"]

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(50))
    sub_category = db.Column(db.String(120))
    github_link = db.Column(db.Text)
    demo_link = db.Column(db.Text)
    description = db.Column(db.Text)
    skills_used = db.Column(db.String(255))
    status = db.Column(db.String(30), default="Planning")
    date_started = db.Column(db.Date)
    date_completed = db.Column(db.Date)
    priority = db.Column(db.String(20), default="Medium")
    notes = db.Column(db.Text)
    is_pinned = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Project {self.title}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    notification_type = db.Column(db.String(50), default="info")
    is_read = db.Column(db.Boolean, default=False)
    related_model = db.Column(db.String(50))
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification {self.title}>"
