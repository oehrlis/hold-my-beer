"""Idempotente Seed-Daten. Loescht niemals Stimmen, Ergebnisse oder Scorecards."""
from ..extensions import db
from ..models import Round, RoundOption, SessionState, Topic

L, M, S = "Leicht", "Mittel", "Schwer"
LOW, MID, HIGH = "Niedrig", "Mittel", "Hoch"

ROUNDS = [
    (1, "Warm-up", [
        ("A", "10G-Passwort-Verifier finden und bereinigen", "Stefan", "Security", L, LOW),
        ("B", "Shell Health-Check für Alert-Log und Listener", "Martin", "Betrieb", L, LOW),
        ("C", "Data Pump Export/Import mit Remap", "Gemeinsam", "Betrieb", L, LOW),
    ]),
    (2, "DBA-Alltag", [
        ("A", "Unified Audit Policy für privilegierte User inklusive NOAUDIT", "Stefan", "Security", M, LOW),
        ("B", "AWR/ASH: Slow Query analysieren", "Martin", "Performance", M, MID),
        ("C", "Listener und sqlnet.ora Hardening", "Gemeinsam", "Security", L, LOW),
    ]),
    (3, "Automation", [
        ("A", "Terraform: DB-System auf OCI", "Stefan", "OCI", M, MID),
        ("B", "Ansible-Playbook für Patching oder Preinstall", "Martin", "Automation", M, MID),
        ("C", "OEM: Metric Extension oder Incident Rule", "Gemeinsam", "OEM", M, MID),
    ]),
    (4, "Bruchstelle", [
        ("A", "TDE-Keystore mit WALLET_ROOT", "Stefan", "Security", M, MID),
        ("B", "Data Guard Switchover mit DGMGRL", "Martin", "Hochverfügbarkeit", S, HIGH),
        ("C", "AI-Code-Review: Fehlerhaftes PL/SQL untersuchen", "Gemeinsam", "Code Review", M, LOW),
    ]),
]

RESERVE = [
    ("Privilege Analysis mit DBMS_PRIVILEGE_CAPTURE", "Security"),
    ("Database Vault Realm für ein Schema", "Security"),
    ("RMAN RECOVER TABLE oder PDB-Restore", "Betrieb"),
    ("ORA-Fehler aus dem Publikum", "Publikum"),
    ("SQL Firewall Allowlist in Oracle AI Database 26ai", "Security"),
    ("Data Safe Assessment interpretieren", "Security"),
    ("OEM-Job mit AI erstellen", "OEM"),
    ("Backup-Strategie automatisieren", "Automation"),
    ("Migrationsskript von Oracle Database 19c nach Oracle AI Database 26ai", "Migration"),
]


def _topic(title, **fields):
    t = Topic.query.filter_by(title=title).first()
    if t is None:
        t = Topic(title=title, **fields)
        db.session.add(t)
        db.session.flush()
    return t


def seed_data():
    for number, name, options in ROUNDS:
        rnd = Round.query.filter_by(number=number).first()
        if rnd is None:
            rnd = Round(number=number, name=name)
            db.session.add(rnd)
            db.session.flush()
        for key, title, owner, cat, diff, risk in options:
            topic = _topic(title, owner=owner, category=cat, difficulty=diff, risk=risk)
            if not RoundOption.query.filter_by(round_id=rnd.id, option=key).first():
                db.session.add(RoundOption(round_id=rnd.id, option=key, topic_id=topic.id))
    for title, cat in RESERVE:
        _topic(title, owner="Offen", category=cat, is_reserve=True)
    if db.session.get(SessionState, 1) is None:
        first = Round.query.order_by(Round.number).first()
        db.session.add(SessionState(id=1, state="waiting", active_round_id=first.id if first else None))
    db.session.commit()


def reset_slots():
    """Setzt die Themenzuordnung aller Runden auf den Seed-Stand zurueck (nach Session-Reset)."""
    RoundOption.query.delete()
    db.session.flush()
    seed_data()
