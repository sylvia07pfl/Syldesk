from flask import Blueprint

library = Blueprint("library", __name__, template_folder="../templates")

from app.library import routes  # noqa: F401, E402
