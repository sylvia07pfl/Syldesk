from flask import Blueprint

dashboard = Blueprint("dashboard", __name__, template_folder="../templates")

from app.dashboard import routes  # noqa: F401, E402
