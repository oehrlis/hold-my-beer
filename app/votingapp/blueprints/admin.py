import hashlib
import hmac
import time
from functools import wraps

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from ..extensions import db, limiter
from ..services import views, voting
from ..services.audit import audit
from ..util import ApiError, ok

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _is_logged_in(touch=True):
    if not session.get("admin"):
        return False
    now = time.time()
    if now - session.get("admin_seen", 0) > current_app.config["ADMIN_IDLE_SECONDS"]:
        session.pop("admin", None)
        return False
    if touch:
        session["admin_seen"] = now
    return True


def admin_required(touch=True):
    def deco(fn):
        @wraps(fn)
        def inner(*a, **kw):
            if not _is_logged_in(touch):
                raise ApiError("unauthorized", "Bitte als Admin anmelden.", 401)
            return fn(*a, **kw)
        return inner
    return deco


def _digest(s):
    return hashlib.sha256(s.encode()).digest()


@bp.get("")
def page():
    if not _is_logged_in():
        return render_template("admin_login.html", error=None)
    default = current_app.config["VOTING_SECONDS"]
    return render_template("admin.html", default_duration=default,
                           durations=sorted({30, 45, 60, 90, 120, default}))


@bp.post("/login")
@limiter.limit(lambda: current_app.config["LOGIN_RATE_LIMIT"])
def login():
    pw = request.form.get("password", "")
    if hmac.compare_digest(_digest(pw), _digest(current_app.config["ADMIN_PASSWORD"])):
        session.clear()
        session["admin"] = True
        session["admin_seen"] = time.time()
        audit("admin_login")
        db.session.commit()
        return redirect(url_for("admin.page"))
    audit("admin_login_failed", "falsches Passwort")
    db.session.commit()
    return render_template("admin_login.html", error="Falsches Passwort."), 401


@bp.post("/logout")
def logout():
    if session.get("admin"):
        audit("admin_logout")
        db.session.commit()
    session.clear()
    return redirect(url_for("admin.page"))


@bp.get("/api/state")
@admin_required(touch=False)  # Polling verlaengert die Session nicht
def state():
    return ok(views.admin_state())


def _need_confirm(body, expected=True):
    if body.get("confirm") != expected:
        raise ApiError("confirmation_required", "Diese Aktion muss ausdrücklich bestätigt werden.", 400)


def _int(body, key):
    try:
        return int(body.get(key))
    except (TypeError, ValueError):
        raise ApiError("invalid_input", "Ungültige Eingabe: %s." % key, 400)


ACTIONS = {
    "activate_round": lambda b: voting.activate_round(_int(b, "round_id")),
    "open_voting": lambda b: voting.open_voting(b.get("duration")),
    "close_voting": lambda b: voting.close_voting(),
    "publish_result": lambda b: voting.publish_result(),
    "runoff": lambda b: (_need_confirm(b), voting.start_runoff(b.get("duration")))[1],
    "select_challenge": lambda b: voting.select_challenge(b.get("option"), b.get("reason")),
    "start_challenge": lambda b: voting.start_challenge(),
    "finish_challenge": lambda b: voting.finish_challenge(),
    "save_scorecard": lambda b: voting.save_scorecard(b.get("ratings"), b.get("note")),
    "next_round": lambda b: voting.next_round(),
    "show_closing": lambda b: voting.show_closing(),
    "save_option": lambda b: voting.save_option(_int(b, "round_id"), b.get("option"), b),
    "delete_option": lambda b: voting.delete_option(_int(b, "round_id"), b.get("option")),
    "assign_reserve": lambda b: voting.assign_reserve(_int(b, "round_id"), b.get("option"), _int(b, "topic_id")),
    "reset_round": lambda b: (_need_confirm(b), voting.reset_round(_int(b, "round_id") if b.get("round_id") else None))[1],
    "set_theme": lambda b: voting.set_theme(b.get("theme")),
    "reset_session": lambda b: (_need_confirm(b, "RESET"), voting.reset_session())[1],
}


@bp.post("/api/<action>")
@admin_required()
def action(action):
    fn = ACTIONS.get(action)
    if fn is None:
        raise ApiError("unknown_action", "Unbekannte Aktion.", 400)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}
    fn(body)
    return ok(views.admin_state(), "Aktion ausgeführt.")


@bp.post("/quick-reset")
@limiter.limit(lambda: current_app.config["LOGIN_RATE_LIMIT"])
def quick_reset():
    """Reset ohne Admin-Session, direkt von der Teilnehmer-/Beamerseite; erfordert das Admin-Passwort im Request."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}
    pw = body.get("password")
    if not isinstance(pw, str) or not hmac.compare_digest(_digest(pw), _digest(current_app.config["ADMIN_PASSWORD"])):
        audit("quick_reset_denied", "falsches Passwort")
        db.session.commit()
        raise ApiError("unauthorized", "Falsches Passwort.", 401)
    if body.get("scope") == "round":
        voting.reset_round()
    elif body.get("scope") == "session":
        voting.reset_session()
    else:
        raise ApiError("invalid_input", "Ungültiger Bereich.", 400)
    return ok({}, "Zurückgesetzt.")
