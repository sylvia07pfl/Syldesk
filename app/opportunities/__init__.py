from flask import Blueprint

opportunities = Blueprint("opportunities", __name__, template_folder="../templates")

from app.opportunities import routes  # noqa: F401, E402
