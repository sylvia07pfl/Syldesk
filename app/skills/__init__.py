from flask import Blueprint

skills = Blueprint("skills", __name__, template_folder="../templates")

from app.skills import routes  # noqa: F401, E402
