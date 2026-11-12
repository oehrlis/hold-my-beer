"""Zustandsdarstellung fuer Teilnehmer/Beamer (oeffentlich) und Admin."""
import time

from flask import current_app

from ..models import AuditLog, Round, RoundOption, Scorecard, Topic
from ..util import iso, utcnow
from . import voting as v


def _remaining(dt):
    return max(0.0, round((dt - utcnow()).total_seconds(), 2)) if dt else None


def _topic_of(rnd, key):
    for o in v.options_of(rnd):
        if o["key"] == key:
            return o
    return None


def _scorecard(rnd):
    card = Scorecard.query.filter_by(round_id=rnd.id).first()
    if card is None:
        return None
    return {"ratings": [{"key": r, "label": v.RATING_LABELS[r]} for r in card.ratings], "note": card.note}


def _result_public(rnd):
    tally = rnd.tally
    if tally is None:
        return None
    res = v.compute_result(rnd, {**{k: 0 for k in v.OPTIONS}, **tally})
    return {"counts": res["counts"], "total": res["total"], "winner": res["winner"], "tie": res["tie"],
            "tied": res["tied"], "selected": rnd.selected_option,
            "deviation_reason": rnd.deviation_reason}


def _closing_summary():
    out = []
    for rnd in Round.query.order_by(Round.number).all():
        sel = _topic_of(rnd, rnd.selected_option) if rnd.selected_option else None
        out.append({"number": rnd.number, "name": rnd.name, "played": rnd.selected_option is not None,
                    "winner": rnd.winner_option, "tie": rnd.is_tie, "selected": rnd.selected_option,
                    "topic": sel["title"] if sel else None, "owner": sel["owner"] if sel else None,
                    "scorecard": _scorecard(rnd)})
    return out


def _build_public(ss):
    rnd = ss.active_round
    data = {"state": ss.state, "round": None, "voting": None, "result": None,
            "challenge": None, "scorecard": None, "closing": None}
    if rnd is not None:
        data["round"] = {"id": rnd.id, "number": rnd.number, "name": rnd.name,
                         "total": Round.query.count(), "options": v.options_of(rnd),
                         "active": v.valid_options(rnd), "runoff": bool(rnd.runoff_options)}
    if rnd is not None and ss.state in ("voting_open", "voting_closed"):
        data["voting"] = {"ends_at": iso(ss.voting_ends_at), "votes": v.vote_total(rnd),
                          "duration": rnd.voting_seconds}
    if rnd is not None and ss.state in ("result_visible", "challenge_running", "scorecard_visible", "closing"):
        data["result"] = _result_public(rnd)
        if rnd.selected_option:
            data["challenge"] = {"topic": _topic_of(rnd, rnd.selected_option), "key": rnd.selected_option,
                                 "ends_at": iso(ss.challenge_ends_at), "started_at": iso(ss.challenge_started_at)}
    if rnd is not None and ss.state in ("scorecard_visible",):
        data["scorecard"] = _scorecard(rnd)
    if ss.state == "closing":
        data["closing"] = _closing_summary()
    data["_ends"] = ss.voting_ends_at if ss.state == "voting_open" else None
    data["_challenge_ends"] = ss.challenge_ends_at if ss.state == "challenge_running" else None
    return data


def public_state(client_hash):
    """Kleine, gecachte Antwort. Waehrend des Votings enthaelt sie nur die Gesamtzahl, keine Zwischenstaende."""
    ss = v.refresh()  # schliesst abgelaufene Votings und invalidiert dann den Cache
    ttl = current_app.config["STATE_CACHE_TTL"]
    cache = current_app.extensions.get("state_cache")
    if ttl and cache and time.monotonic() - cache[0] < ttl:
        base = cache[1]
    else:
        base = _build_public(ss)
        current_app.extensions["state_cache"] = (time.monotonic(), base)
    data = {k: val for k, val in base.items() if not k.startswith("_")}
    data["server_time"] = iso(utcnow())
    if data["voting"] is not None:
        data["voting"] = dict(data["voting"], remaining=_remaining(base["_ends"]))
    if data["challenge"] is not None:
        data["challenge"] = dict(data["challenge"], remaining=_remaining(base["_challenge_ends"]))
    data["my_vote"] = v.my_vote(client_hash, ss.active_round)
    return data


def admin_state():
    ss = v.refresh()
    rnd = ss.active_round
    data = _build_public(ss)
    data = {k: val for k, val in data.items() if not k.startswith("_")}
    data["server_time"] = iso(utcnow())
    data["updated_at"] = iso(ss.updated_at)
    if data["voting"] is not None:
        data["voting"]["remaining"] = _remaining(ss.voting_ends_at)
    if data["challenge"] is not None:
        data["challenge"]["remaining"] = _remaining(ss.challenge_ends_at)
    if rnd is not None:
        res = v.compute_result(rnd)
        data["live"] = {**res, "selected": rnd.selected_option, "deviation_reason": rnd.deviation_reason}
        if ss.state == "challenge_running" or rnd.selected_option:
            data["challenge"] = data["challenge"] or {"topic": _topic_of(rnd, rnd.selected_option),
                                                      "key": rnd.selected_option, "remaining": None}
        data["scorecard"] = _scorecard(rnd)
    else:
        data["live"] = None
    data["rounds"] = [{"id": r.id, "number": r.number, "name": r.name,
                       "options": v.options_of(r), "played": r.selected_option is not None,
                       "votes": v.vote_total(r)}
                      for r in Round.query.order_by(Round.number).all()]
    used = {o.topic_id for o in RoundOption.query.all()}
    data["reserve"] = [{"id": t.id, "title": t.title, "category": t.category, "used": t.id in used}
                       for t in Topic.query.filter_by(is_reserve=True).order_by(Topic.id).all()]
    data["ratings"] = [{"key": k, "label": label} for k, label in v.RATINGS]
    data["audit"] = [{"at": iso(a.at), "actor": a.actor, "action": a.action, "detail": a.detail}
                     for a in AuditLog.query.order_by(AuditLog.id.desc()).limit(40).all()]
    data["min_duration"], data["max_duration"] = v.MIN_DURATION, v.MAX_DURATION
    return data
