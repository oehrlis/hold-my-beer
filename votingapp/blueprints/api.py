import re

from flask import Blueprint, current_app, request
from sqlalchemy import inspect, text

from ..clientid import get_client_id, hash_client_id, rate_key
from ..extensions import db, limiter
from ..services import views, voting
from ..util import ApiError, ok

bp = Blueprint("api", __name__)
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
REQUIRED_TABLES = {"session_state", "round", "round_option", "topic", "vote", "scorecard", "audit_log"}


@bp.get("/api/state")
def state():
    cid = get_client_id(create=True)  # setzt das Cookie schon beim ersten Poll
    return ok(views.public_state(hash_client_id(cid)))


@bp.post("/api/vote")
@limiter.limit(lambda: current_app.config["VOTE_RATE_LIMIT"], key_func=rate_key)
def vote():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("invalid_input", "Ungültige Anfrage.", 400)
    option, request_id = body.get("option"), body.get("request_id")
    if option not in voting.OPTIONS:
        raise ApiError("invalid_option", "Ungültige Option.", 400)
    if not isinstance(request_id, str) or not REQUEST_ID.match(request_id):
        raise ApiError("invalid_request_id", "Ungültige Anfrage-ID.", 400)
    cid = get_client_id(create=True)
    stored, repeated = voting.cast_vote(hash_client_id(cid), option, request_id)
    return ok({"option": stored.option, "repeated": repeated}, "Deine Stimme wurde gespeichert.")


@bp.get("/healthz")
def healthz():
    return ok({"status": "alive"})


@bp.get("/readyz")
def readyz():
    try:
        db.session.execute(text("SELECT 1"))
        missing = REQUIRED_TABLES - set(inspect(db.engine).get_table_names())
        if missing:
            raise ApiError("not_ready", "Datenbankschema unvollständig.", 503)
        voting.get_ss()
    except ApiError:
        raise
    except Exception:
        raise ApiError("not_ready", "Datenbank nicht erreichbar.", 503)
    return ok({"status": "ready"})
