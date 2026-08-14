from flask import Blueprint

backup = Blueprint("backup", __name__, template_folder="../templates")

from app.backup import routes  # noqa: F401, E402
