"""SQLite-Backup (Online-Backup-API) und JSON-Export."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import current_app

from ..extensions import db
from ..models import AuditLog, Round, Scorecard, Topic, Vote
from ..util import iso


def db_path():
    url = db.engine.url
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise RuntimeError("Backup nur für SQLite-Dateidatenbanken verfügbar.")
    return url.database


def backup_database(dest_dir=None):
    dest = Path(dest_dir or current_app.config["BACKUP_DIR"])
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / ("voting-%s.db" % datetime.now().strftime("%Y%m%d-%H%M%S"))
    src = sqlite3.connect(db_path(), timeout=5)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)  # konsistenter Snapshot auch bei laufender Anwendung
    finally:
        dst.close()
        src.close()
    target.chmod(0o600)
    return target


def export_data():
    from .voting import options_of
    rounds = []
    for r in Round.query.order_by(Round.number).all():
        card = Scorecard.query.filter_by(round_id=r.id).first()
        rounds.append({
            "number": r.number, "name": r.name, "options": options_of(r),
            "voting_seconds": r.voting_seconds, "runoff_options": r.runoff_options,
            "result": {"tally": r.tally, "winner": r.winner_option, "tie": r.is_tie,
                       "published_at": iso(r.result_published_at)},
            "challenge": {"selected": r.selected_option, "deviation_reason": r.deviation_reason,
                          "selected_at": iso(r.selected_at)},
            "votes": [{"option": x.option, "client_hash_prefix": x.client_hash[:8], "at": iso(x.created_at)}
                      for x in Vote.query.filter_by(round_id=r.id).order_by(Vote.id)],
            "scorecard": {"ratings": card.ratings, "note": card.note} if card else None,
        })
    return {"exported_at": iso(datetime.utcnow()), "rounds": rounds,
            "reserve_topics": [t.as_dict() for t in Topic.query.filter_by(is_reserve=True)],
            "audit": [{"at": iso(a.at), "actor": a.actor, "action": a.action, "detail": a.detail}
                      for a in AuditLog.query.order_by(AuditLog.id)]}


def export_json(path=None):
    text = json.dumps(export_data(), ensure_ascii=False, indent=2)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return text
