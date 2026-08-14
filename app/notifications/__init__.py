from flask import Blueprint

notifications = Blueprint("notifications", __name__, template_folder="../templates")

from app.notifications import routes  # noqa: F401, E402
