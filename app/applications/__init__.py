from flask import Blueprint

applications = Blueprint("applications", __name__, template_folder="../templates")

from app.applications import routes  # noqa: F401, E402
