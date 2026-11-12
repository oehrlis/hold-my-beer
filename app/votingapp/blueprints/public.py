from flask import Blueprint, current_app, render_template

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    return render_template("index.html")
