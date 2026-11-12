"""Idempotente Seed-Daten aus der Pool-Datei (POOL_FILE). Loescht niemals Stimmen, Ergebnisse oder Scorecards.

Verhalten bei einer bestehenden Datenbank:
- fehlende Runden, Optionen und Themen werden angelegt, bestehende nie veraendert
  (Admin-Aenderungen und Reserve-Zuordnungen ueberleben jeden Start);
- Abweichungen zum Pool (z.B. Runde 4 aus dem alten eingebauten Seed) werden als Warnung gemeldet;
- erst reset_slots() (Admin "Gesamte Session zuruecksetzen") gleicht Runden und Optionen an den Pool an.
"""
from flask import current_app

from ..extensions import db
from ..models import Round, RoundOption, Scorecard, SessionState, Topic, Vote
from ..pool import PoolError, load_pool


def _pool(pool):
    if pool is None or isinstance(pool, str):
        return load_pool(pool or current_app.config.get("POOL_FILE"))
    return pool


def check_scorecard(pool):
    """Jede Scorecard-Kategorie des Pools muss eine bekannte Bewertung der App sein."""
    from .voting import RATINGS
    known = {label.casefold(): key for key, label in RATINGS}
    unknown = [c for c in pool["format"]["scorecard"] if c.casefold() not in known]
    if unknown:
        raise PoolError("Scorecard-Kategorie(n) aus dem Pool unbekannt: %s (bekannt: %s)"
                        % (", ".join(unknown), ", ".join(label for _, label in RATINGS)))
    return [known[c.casefold()] for c in pool["format"]["scorecard"]]


def _topic(title, **fields):
    t = Topic.query.filter_by(title=title).first()
    if t is None:
        t = Topic(title=title, **fields)
        db.session.add(t)
        db.session.flush()
    return t


def _has_results(rnd):
    return bool(Vote.query.filter_by(round_id=rnd.id).count() or Scorecard.query.filter_by(round_id=rnd.id).count())


def _drift(pool):
    """Meldet, wo die Datenbank vom Pool abweicht (nur lesen)."""
    warnings = []
    by_number = {r["number"]: r for r in pool["rounds"]}
    for rnd in Round.query.order_by(Round.number).all():
        spec = by_number.get(rnd.number)
        if spec is None:
            warnings.append("Runde %d '%s' steht nicht im Pool und bleibt erhalten%s. Fuer den Talk: frische DB "
                            "oder Admin 'Gesamte Session zuruecksetzen'."
                            % (rnd.number, rnd.name, " (hat Stimmen/Scorecard)" if _has_results(rnd) else ""))
            continue
        if rnd.name != spec["name"]:
            warnings.append("Runde %d heisst in der DB '%s', im Pool '%s'." % (rnd.number, rnd.name, spec["name"]))
        db_opts = {o.option: o.topic.title for o in rnd.options}
        for o in spec["options"]:
            have = db_opts.get(o["key"])
            if have is not None and have != o["title"]:
                warnings.append("Runde %d, %s: DB '%s', Pool '%s' (Admin-Aenderung oder alter Seed)."
                                % (rnd.number, o["key"], have, o["title"]))
    return warnings


def seed_data(pool=None):
    """Legt fehlende Runden, Optionen und Reserve-Themen aus dem Pool an.

    pool: None (POOL_FILE aus der Konfiguration), ein Pfad oder ein bereits geladenes Pool-dict.
    Liefert {"path", "rounds", "options", "reserve", "warnings"}. Wirft PoolError bei fehlender/ungueltiger Datei.
    """
    pool = _pool(pool)
    check_scorecard(pool)
    used = {o.topic_id for o in RoundOption.query.all()}
    for spec in pool["rounds"]:
        rnd = Round.query.filter_by(number=spec["number"]).first()
        if rnd is None:
            rnd = Round(number=spec["number"], name=spec["name"])
            db.session.add(rnd)
            db.session.flush()
        for o in spec["options"]:
            topic = _topic(o["title"], owner=o["owner"], category=o["category"],
                           difficulty=o["difficulty"], risk=o["risk"])
            if not RoundOption.query.filter_by(round_id=rnd.id, option=o["key"]).first():
                db.session.add(RoundOption(round_id=rnd.id, option=o["key"], topic_id=topic.id))
                used.add(topic.id)
    for t in pool["reserve"]:
        topic = _topic(t["title"], owner=t["owner"], category=t["category"], is_reserve=True)
        if not topic.is_reserve and topic.id not in used:
            topic.is_reserve = True  # z.B. frueheres Rundenthema, das jetzt Reserve ist
    if db.session.get(SessionState, 1) is None:
        first = Round.query.order_by(Round.number).first()
        db.session.add(SessionState(id=1, state="waiting", active_round_id=first.id if first else None))
    db.session.flush()
    warnings = _drift(pool)
    db.session.commit()
    return {"path": pool.get("path"), "rounds": len(pool["rounds"]),
            "options": sum(len(r["options"]) for r in pool["rounds"]),
            "reserve": len(pool["reserve"]), "warnings": warnings}


def reset_slots(pool=None):
    """Gleicht Runden und Themenzuordnung an den Pool an (nach Session-Reset, Stimmen sind dann geloescht).

    Runden, die nicht im Pool stehen, werden nur entfernt, wenn sie weder Stimmen noch Scorecard haben.
    """
    pool = _pool(pool)
    check_scorecard(pool)
    specs = {r["number"]: r for r in pool["rounds"]}
    RoundOption.query.delete()
    ss = db.session.get(SessionState, 1)
    for rnd in Round.query.all():
        spec = specs.get(rnd.number)
        if spec is not None:
            rnd.name = spec["name"]
        elif not _has_results(rnd):
            if ss is not None and ss.active_round_id == rnd.id:
                ss.active_round_id = None
            db.session.delete(rnd)
    db.session.flush()
    return seed_data(pool)
