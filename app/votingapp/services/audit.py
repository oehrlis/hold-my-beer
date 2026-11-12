import logging

from ..extensions import db
from ..models import AuditLog

log = logging.getLogger("votingapp.audit")


def audit(action, detail=None, actor="admin"):
    """Fuegt einen Auditeintrag zur laufenden Transaktion hinzu (Commit macht der Aufrufer)."""
    detail = (detail or "")[:500] or None
    db.session.add(AuditLog(action=action, detail=detail, actor=actor))
    log.info("audit actor=%s action=%s detail=%s", actor, action, detail)


def log_startup():
    try:
        audit("app_start", actor="system")
        db.session.commit()
    except Exception:  # Schema evtl. noch nicht vorhanden
        db.session.rollback()
