from flask import Blueprint

inspiration = Blueprint("inspiration", __name__, template_folder="../templates")

from app.inspiration import routes  # noqa: F401, E402
