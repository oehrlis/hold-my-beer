"""Kernlogik: Zustandswechsel, Stimmabgabe, Ergebnis, Challenge, Scorecard, Resets.

Alle Zeitentscheidungen laufen serverseitig in UTC. Schreibtransaktionen bleiben kurz.
"""
import json
from datetime import timedelta

from flask import current_app
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError, OperationalError

from ..extensions import db
from ..models import Round, RoundOption, Scorecard, SessionState, Topic, Vote
from ..util import ApiError, utcnow
from . import seed
from .audit import audit
from .state_machine import check_transition

OPTIONS = ("A", "B", "C", "D")
MAX_OPTIONS, MIN_OPTIONS = 4, 2
DIFFICULTIES = ("Leicht", "Mittel", "Schwer")
RISKS = ("Niedrig", "Mittel", "Hoch")
RATINGS = [
    ("ai_correct", "AI richtig"),
    ("ai_hallucinated", "AI halluziniert"),
    ("wrong_problem", "falsches Problem gelöst"),
    ("dba_instinct", "DBA-Instinkt gewinnt"),
    ("human_with_ai", "Mensch mit AI gewinnt"),
    ("task_done", "Aufgabe erfolgreich abgeschlossen"),
    ("task_partial", "Aufgabe teilweise abgeschlossen"),
    ("task_failed", "Aufgabe nicht abgeschlossen"),
]
RATING_LABELS = dict(RATINGS)
MIN_DURATION, MAX_DURATION = 10, 600


# ---------------------------------------------------------------- Grundzugriff
def invalidate_cache():
    current_app.extensions.pop("state_cache", None)


def get_ss():
    ss = db.session.get(SessionState, 1)
    if ss is None:
        raise ApiError("not_seeded", "Die Datenbank ist nicht initialisiert.", 503)
    return ss


def _commit():
    try:
        db.session.commit()
    except OperationalError:
        db.session.rollback()
        raise ApiError("busy", "Server kurz ausgelastet, bitte erneut versuchen.", 503)
    invalidate_cache()


def refresh():
    """Liefert den Session-Zustand; schliesst ein abgelaufenes Voting atomar."""
    ss = get_ss()
    if ss.state == "voting_open" and ss.voting_ends_at and ss.voting_ends_at <= utcnow():
        res = db.session.execute(
            update(SessionState)
            .where(SessionState.id == 1, SessionState.state == "voting_open")
            .values(state="voting_closed", updated_at=utcnow()))
        if res.rowcount:
            audit("voting_closed", "automatisch, Zeit abgelaufen", actor="system")
            if current_app.config["AUTO_PUBLISH_RESULT"]:
                _publish(get_ss(), actor="system")
        _commit()
        ss = get_ss()
    return ss


def valid_options(rnd):
    return rnd.runoff_options.split(",") if rnd.runoff_options else [o.option for o in rnd.options]


def options_of(rnd):
    return [{"key": o.option, **o.topic.as_dict()} for o in rnd.options]


def counts_of(rnd):
    rows = db.session.query(Vote.option, func.count(Vote.id)).filter(
        Vote.round_id == rnd.id).group_by(Vote.option).all()
    counts = {k: 0 for k in OPTIONS}
    counts.update(dict(rows))
    return counts


def vote_total(rnd):
    return db.session.query(func.count(Vote.id)).filter(Vote.round_id == rnd.id).scalar() or 0


def compute_result(rnd, counts=None):
    counts = counts or counts_of(rnd)
    valid = valid_options(rnd)
    total = sum(counts[k] for k in valid)
    top = max((counts[k] for k in valid), default=0)
    leaders = [k for k in valid if counts[k] == top] if top > 0 else []
    winner = leaders[0] if len(leaders) == 1 else None
    runner_up = None
    if winner:
        rest = sorted({counts[k] for k in valid if k != winner}, reverse=True)
        if rest and rest[0] > 0:
            second = [k for k in valid if k != winner and counts[k] == rest[0]]
            runner_up = second[0] if len(second) == 1 else None
    return {"counts": counts, "total": total, "winner": winner,
            "tie": len(leaders) > 1, "tied": leaders if len(leaders) > 1 else [],
            "runner_up": runner_up}


def active_round(ss=None):
    ss = ss or get_ss()
    return ss.active_round


def _transition(ss, new, **fields):
    check_transition(ss.state, new)
    ss.state = new
    ss.updated_at = utcnow()
    for k, v in fields.items():
        setattr(ss, k, v)


def _need_round(ss):
    rnd = ss.active_round
    if rnd is None:
        raise ApiError("no_active_round", "Es ist keine Runde aktiv.", 409)
    return rnd


def _clear_round(rnd):
    Vote.query.filter_by(round_id=rnd.id).delete()
    Scorecard.query.filter_by(round_id=rnd.id).delete()
    rnd.tally_json = rnd.winner_option = rnd.runoff_options = None
    rnd.is_tie = False
    rnd.result_published_at = rnd.selected_at = None
    rnd.selected_option = rnd.deviation_reason = rnd.voting_seconds = None


# ---------------------------------------------------------------- Teilnehmer
def cast_vote(client_hash, option, request_id):
    """Speichert genau eine Stimme pro Runde und Client. Retry mit gleicher request_id ist idempotent."""
    ss = refresh()
    now = utcnow()
    if ss.state != "voting_open" or not ss.voting_ends_at or ss.voting_ends_at <= now:
        raise ApiError("voting_closed", "Das Voting ist nicht geöffnet.", 403)
    rnd = _need_round(ss)
    if option not in valid_options(rnd):
        raise ApiError("invalid_option", "Ungültige Option.", 400)

    def existing():
        return Vote.query.filter_by(round_id=rnd.id, client_hash=client_hash).first()

    def settle(v):
        if v is None:
            return None
        if v.request_id == request_id:
            return v, True
        raise ApiError("already_voted", "Du hast in dieser Runde bereits abgestimmt.", 409)

    hit = settle(existing())
    if hit:
        return hit
    db.session.add(Vote(round_id=rnd.id, client_hash=client_hash, option=option, request_id=request_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        hit = settle(existing())
        if hit:
            return hit
        raise ApiError("duplicate_request", "Ungültige Anfrage-ID.", 400)
    except OperationalError:
        db.session.rollback()
        raise ApiError("busy", "Server kurz ausgelastet, bitte erneut versuchen.", 503)
    return existing(), False


def my_vote(client_hash, rnd):
    if not client_hash or rnd is None:
        return None
    v = Vote.query.filter_by(round_id=rnd.id, client_hash=client_hash).first()
    return v.option if v else None


# ---------------------------------------------------------------- Admin-Aktionen
def activate_round(round_id):
    ss = refresh()
    if ss.state != "waiting":
        raise ApiError("invalid_transition", "Runden können nur im Zustand 'waiting' aktiviert werden.", 409)
    rnd = db.session.get(Round, round_id)
    if rnd is None:
        raise ApiError("unknown_round", "Unbekannte Runde.", 400)
    ss.active_round_id = rnd.id
    ss.updated_at = utcnow()
    audit("round_activated", "Runde %d" % rnd.number)
    _commit()


def _parse_duration(value):
    try:
        d = int(value)
    except (TypeError, ValueError):
        raise ApiError("invalid_duration", "Ungültige Dauer.", 400)
    if not MIN_DURATION <= d <= MAX_DURATION:
        raise ApiError("invalid_duration", "Die Dauer muss zwischen %d und %d Sekunden liegen."
                       % (MIN_DURATION, MAX_DURATION), 400)
    return d


def open_voting(duration):
    duration = _parse_duration(duration)
    ss = refresh()
    check_transition(ss.state, "voting_open")
    rnd = _need_round(ss)
    if rnd.result_published_at or vote_total(rnd):
        raise ApiError("round_already_played", "Diese Runde hat bereits Stimmen. Bitte zuerst zurücksetzen.", 409)
    now = utcnow()
    _transition(ss, "voting_open", voting_started_at=now, voting_ends_at=now + timedelta(seconds=duration),
                challenge_started_at=None, challenge_ends_at=None)
    rnd.voting_seconds = duration
    audit("voting_opened", "Runde %d, %d s" % (rnd.number, duration))
    _commit()


def close_voting():
    ss = refresh()
    check_transition(ss.state, "voting_closed")
    _transition(ss, "voting_closed", voting_ends_at=min(ss.voting_ends_at, utcnow()))
    audit("voting_closed", "manuell, Runde %d" % _need_round(ss).number)
    if current_app.config["AUTO_PUBLISH_RESULT"]:
        _publish(ss)
    _commit()


def _publish(ss, actor="admin"):
    check_transition(ss.state, "result_visible")
    rnd = _need_round(ss)
    res = compute_result(rnd)
    rnd.tally_json = json.dumps(res["counts"])
    rnd.winner_option = res["winner"]
    rnd.is_tie = res["tie"]
    rnd.result_published_at = utcnow()
    _transition(ss, "result_visible")
    audit("result_published", "Runde %d: %s" % (rnd.number, json.dumps(res["counts"])), actor=actor)


def publish_result():
    ss = refresh()
    _publish(ss)
    _commit()


def start_runoff(duration):
    """Stichwahl bei Gleichstand: nur die gleichplatzierten Optionen, Stimmen der Runde werden verworfen."""
    duration = _parse_duration(duration)
    ss = refresh()
    if ss.state not in ("voting_closed", "result_visible"):
        raise ApiError("invalid_transition", "Eine Stichwahl ist nur nach geschlossenem Voting möglich.", 409)
    rnd = _need_round(ss)
    res = compute_result(rnd)
    if not res["tie"]:
        raise ApiError("no_tie", "Es liegt kein Gleichstand vor.", 409)
    audit("runoff_started", "Runde %d, Gleichstand %s, Stimmen %s" % (
        rnd.number, ",".join(res["tied"]), json.dumps(res["counts"])))
    _clear_round(rnd)
    rnd.runoff_options = ",".join(res["tied"])
    rnd.voting_seconds = duration
    now = utcnow()
    ss.state = "voting_open"
    ss.voting_started_at, ss.voting_ends_at = now, now + timedelta(seconds=duration)
    ss.challenge_started_at = ss.challenge_ends_at = None
    ss.updated_at = now
    _commit()


def select_challenge(option, reason):
    ss = refresh()
    if ss.state != "result_visible":
        raise ApiError("invalid_transition", "Das Challenge-Thema kann nur nach der Ergebnisfreigabe gewählt werden.", 409)
    rnd = _need_round(ss)
    if option not in valid_options(rnd):
        raise ApiError("invalid_option", "Ungültige Option.", 400)
    reason = (reason or "").strip()[:300]
    res = compute_result(rnd)
    deviation = res["winner"] is not None and option != res["winner"]
    if deviation and not reason:
        raise ApiError("reason_required", "Für eine Abweichung vom Abstimmungsergebnis ist eine Begründung nötig.", 400)
    rnd.selected_option = option
    rnd.selected_at = utcnow()
    rnd.deviation_reason = reason if (deviation or res["tie"]) and reason else None
    audit("challenge_selected_manual", "Runde %d: %s (Gewinner: %s)%s" % (
        rnd.number, option, res["winner"] or "Gleichstand", ", Begründung: " + reason if reason else ""))
    _commit()


def start_challenge():
    ss = refresh()
    check_transition(ss.state, "challenge_running")
    rnd = _need_round(ss)
    if rnd.selected_option is None:
        res = compute_result(rnd)
        if res["winner"] is None:
            raise ApiError("challenge_not_selected", "Bitte zuerst ein Challenge-Thema auswählen.", 409)
        rnd.selected_option, rnd.selected_at = res["winner"], utcnow()
        audit("challenge_selected_winner", "Runde %d: %s" % (rnd.number, res["winner"]))
    now = utcnow()
    secs = current_app.config["CHALLENGE_SECONDS"]
    _transition(ss, "challenge_running", challenge_started_at=now, challenge_ends_at=now + timedelta(seconds=secs))
    audit("challenge_started", "Runde %d, Thema %s" % (rnd.number, rnd.selected_option))
    _commit()


def finish_challenge():
    ss = refresh()
    check_transition(ss.state, "scorecard_visible")
    _transition(ss, "scorecard_visible")
    audit("challenge_stopped", "Runde %d" % _need_round(ss).number)
    _commit()


def save_scorecard(ratings, note):
    ss = refresh()
    if ss.state != "scorecard_visible":
        raise ApiError("invalid_transition", "Die Scorecard kann nur im Zustand 'scorecard_visible' erfasst werden.", 409)
    if not isinstance(ratings, list) or any(r not in RATING_LABELS for r in ratings):
        raise ApiError("invalid_rating", "Ungültige Bewertung.", 400)
    note = (note or "").strip()
    if len(note) > 300:
        raise ApiError("note_too_long", "Die Bemerkung ist zu lang (max. 300 Zeichen).", 400)
    rnd = _need_round(ss)
    card = Scorecard.query.filter_by(round_id=rnd.id).first() or Scorecard(round_id=rnd.id)
    card.ratings_json = json.dumps(sorted(set(ratings), key=[r for r, _ in RATINGS].index))
    card.note = note or None
    card.updated_at = utcnow()
    db.session.add(card)
    audit("scorecard_saved", "Runde %d" % rnd.number)
    _commit()


def next_round():
    ss = refresh()
    check_transition(ss.state, "waiting")
    rnd = _need_round(ss)
    nxt = Round.query.filter(Round.number > rnd.number).order_by(Round.number).first()
    if nxt is None:
        raise ApiError("no_next_round", "Es gibt keine weitere Runde. Bitte das Closing anzeigen.", 409)
    _transition(ss, "waiting", active_round_id=nxt.id, voting_started_at=None, voting_ends_at=None,
                challenge_started_at=None, challenge_ends_at=None)
    audit("round_activated", "Runde %d (nächste Runde)" % nxt.number)
    _commit()


def show_closing():
    ss = refresh()
    check_transition(ss.state, "closing")
    _transition(ss, "closing")
    audit("closing_shown")
    _commit()


def assign_reserve(round_id, option, topic_id):
    ss = refresh()
    if ss.state != "waiting":
        raise ApiError("invalid_transition", "Reserve-Themen können nur im Zustand 'waiting' zugeordnet werden.", 409)
    rnd = db.session.get(Round, round_id)
    topic = db.session.get(Topic, topic_id)
    if rnd is None or topic is None or not topic.is_reserve or option not in OPTIONS:
        raise ApiError("invalid_input", "Ungültige Runde, Option oder Reserve-Thema.", 400)
    if rnd.result_published_at or vote_total(rnd):
        raise ApiError("round_already_played", "Diese Runde hat bereits Stimmen.", 409)
    slot = RoundOption.query.filter_by(round_id=rnd.id, option=option).first()
    if slot is None:
        raise ApiError("invalid_input", "Diese Option existiert in der Runde nicht.", 400)
    old = slot.topic.title
    slot.topic_id = topic.id
    audit("reserve_assigned", "Runde %d, %s: '%s' ersetzt durch '%s'" % (rnd.number, option, old, topic.title))
    _commit()


def reset_round(round_id=None):
    ss = refresh()
    rnd = db.session.get(Round, round_id) if round_id else ss.active_round
    if rnd is None:
        raise ApiError("unknown_round", "Unbekannte Runde.", 400)
    _clear_round(rnd)
    ss.state, ss.active_round_id, ss.updated_at = "waiting", rnd.id, utcnow()
    ss.voting_started_at = ss.voting_ends_at = ss.challenge_started_at = ss.challenge_ends_at = None
    audit("reset_round", "Runde %d" % rnd.number)
    _commit()


def reset_session():
    ss = refresh()
    for rnd in Round.query.all():
        _clear_round(rnd)
    seed.reset_slots()
    ss = get_ss()
    first = Round.query.order_by(Round.number).first()
    ss.state, ss.active_round_id, ss.updated_at = "waiting", first.id, utcnow()
    ss.voting_started_at = ss.voting_ends_at = ss.challenge_started_at = ss.challenge_ends_at = None
    audit("reset_session", "gesamte Session zurückgesetzt")
    _commit()


# ---------------------------------------------------------------- Aufgaben bearbeiten
def _clean_topic(fields):
    def text(key, maxlen, required=False):
        val = (fields.get(key) or "")
        if not isinstance(val, str):
            raise ApiError("invalid_input", "Ungültige Eingabe: %s." % key, 400)
        val = " ".join(val.split())
        if required and not val:
            raise ApiError("invalid_input", "Der Titel darf nicht leer sein.", 400)
        if len(val) > maxlen:
            raise ApiError("invalid_input", "%s ist zu lang (max. %d Zeichen)." % (key, maxlen), 400)
        return val

    out = {"title": text("title", 200, True), "owner": text("owner", 40) or "Gemeinsam",
           "category": text("category", 60), "difficulty": text("difficulty", 20) or None,
           "risk": text("risk", 20) or None}
    if out["difficulty"] not in (None,) + DIFFICULTIES or out["risk"] not in (None,) + RISKS:
        raise ApiError("invalid_input", "Ungültige Schwierigkeit oder ungültiges Live-Risiko.", 400)
    return out


def _editable_round(round_id):
    ss = refresh()
    if ss.state != "waiting":
        raise ApiError("invalid_transition", "Aufgaben können nur im Zustand 'waiting' bearbeitet werden.", 409)
    rnd = db.session.get(Round, round_id)
    if rnd is None:
        raise ApiError("unknown_round", "Unbekannte Runde.", 400)
    if rnd.result_published_at or vote_total(rnd):
        raise ApiError("round_already_played", "Diese Runde hat bereits Stimmen. Bitte zuerst zurücksetzen.", 409)
    return rnd


def _in_use_elsewhere(topic, except_slot_id=None):
    q = RoundOption.query.filter(RoundOption.topic_id == topic.id)
    if except_slot_id:
        q = q.filter(RoundOption.id != except_slot_id)
    return q.count() > 0


def _topic_for(clean, slot=None):
    """Liefert das Topic fuer die Eingaben. Geteilte Topics (Reserve, in anderer Runde genutzt) werden nie veraendert."""
    current = slot.topic if slot else None
    other = Topic.query.filter(Topic.title == clean["title"], Topic.id != (current.id if current else 0)).first()
    if other is not None:
        if other.is_reserve or _in_use_elsewhere(other):
            raise ApiError("duplicate_title", "Dieser Titel wird bereits für eine andere Aufgabe verwendet.", 409)
        topic = other  # verwaister Eintrag: wiederverwenden
    elif current is not None and not current.is_reserve and not _in_use_elsewhere(current, slot.id):
        topic = current  # exklusiv genutzt: direkt bearbeiten
    else:
        topic = Topic(title=clean["title"])
        db.session.add(topic)
    topic.title, topic.owner, topic.category = clean["title"], clean["owner"], clean["category"]
    topic.difficulty, topic.risk, topic.is_reserve = clean["difficulty"], clean["risk"], False
    db.session.flush()
    return topic


def save_option(round_id, option, fields):
    """Bearbeitet die Aufgabe einer Option oder legt (bis max. 4) eine neue an (option leer oder 'new')."""
    rnd = _editable_round(round_id)
    clean = _clean_topic(fields)
    keys = [o.option for o in rnd.options]
    slot = None
    if option and option != "new":
        slot = RoundOption.query.filter_by(round_id=rnd.id, option=option).first()
        if slot is None:
            raise ApiError("invalid_option", "Diese Option existiert nicht.", 400)
    elif len(keys) >= MAX_OPTIONS:
        raise ApiError("max_options", "Pro Runde sind maximal %d Aufgaben möglich." % MAX_OPTIONS, 409)
    topic = _topic_for(clean, slot)
    if slot is None:
        key = OPTIONS[len(keys)]
        db.session.add(RoundOption(round_id=rnd.id, option=key, topic_id=topic.id))
        audit("option_added", "Runde %d, %s: '%s'" % (rnd.number, key, topic.title))
    else:
        old_title = slot.topic.title
        slot.topic_id = topic.id
        audit("option_edited", "Runde %d, %s: '%s' -> '%s'" % (rnd.number, slot.option, old_title, topic.title))
    _commit()


def delete_option(round_id, option):
    rnd = _editable_round(round_id)
    slots = list(rnd.options)
    if len(slots) <= MIN_OPTIONS:
        raise ApiError("min_options", "Pro Runde sind mindestens %d Aufgaben nötig." % MIN_OPTIONS, 409)
    slot = next((o for o in slots if o.option == option), None)
    if slot is None:
        raise ApiError("invalid_option", "Diese Option existiert nicht.", 400)
    title = slot.topic.title
    db.session.delete(slot)
    db.session.flush()
    # Buchstaben lueckenlos neu vergeben (A, B, C ...); aufsteigend, daher nie Konflikte
    for new_key, o in zip(OPTIONS, [x for x in slots if x is not slot]):
        o.option = new_key
    audit("option_deleted", "Runde %d, %s: '%s'" % (rnd.number, option, title))
    _commit()
