from flask import render_template
from app.main import main


@main.route("/")
def landing():
    return render_template("landing.html")
