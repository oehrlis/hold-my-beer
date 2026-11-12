import json

from .extensions import db
from .util import utcnow


class Topic(db.Model):
    __tablename__ = "topic"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, unique=True)
    owner = db.Column(db.String(40), nullable=False, default="Gemeinsam")
    category = db.Column(db.String(60), nullable=False, default="")
    difficulty = db.Column(db.String(20))
    risk = db.Column(db.String(20))
    is_reserve = db.Column(db.Boolean, nullable=False, default=False)

    def as_dict(self):
        return {"title": self.title, "owner": self.owner, "category": self.category,
                "difficulty": self.difficulty, "risk": self.risk, "reserve": self.is_reserve}


class Round(db.Model):
    __tablename__ = "round"
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(80), nullable=False)
    voting_seconds = db.Column(db.Integer)
    # Abstimmungsergebnis (Snapshot bei Freigabe) - getrennt von der Challenge-Auswahl
    tally_json = db.Column(db.Text)
    winner_option = db.Column(db.String(1))
    is_tie = db.Column(db.Boolean, nullable=False, default=False)
    result_published_at = db.Column(db.DateTime)
    runoff_options = db.Column(db.String(10))  # z.B. "A,B" bei Stichwahl
    # ausgewaehltes Challenge-Thema (kann vom Gewinner abweichen)
    selected_option = db.Column(db.String(1))
    deviation_reason = db.Column(db.String(300))
    selected_at = db.Column(db.DateTime)

    options = db.relationship("RoundOption", back_populates="round", order_by="RoundOption.option",
                              cascade="all, delete-orphan")

    @property
    def tally(self):
        return json.loads(self.tally_json) if self.tally_json else None


class RoundOption(db.Model):
    __tablename__ = "round_option"
    __table_args__ = (db.UniqueConstraint("round_id", "option", name="uq_round_option"),
                      db.CheckConstraint("option IN ('A','B','C','D')", name="ck_round_option_key"))
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False)
    option = db.Column(db.String(1), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False)

    round = db.relationship("Round", back_populates="options")
    topic = db.relationship("Topic")


class SessionState(db.Model):
    __tablename__ = "session_state"
    id = db.Column(db.Integer, primary_key=True)  # immer genau eine Zeile (id=1)
    state = db.Column(db.String(30), nullable=False, default="waiting")
    active_round_id = db.Column(db.Integer, db.ForeignKey("round.id"))
    voting_started_at = db.Column(db.DateTime)
    voting_ends_at = db.Column(db.DateTime)
    challenge_started_at = db.Column(db.DateTime)
    challenge_ends_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    active_round = db.relationship("Round")


class Vote(db.Model):
    __tablename__ = "vote"
    __table_args__ = (
        db.UniqueConstraint("round_id", "client_hash", name="uq_vote_round_client"),
        db.CheckConstraint("option IN ('A','B','C','D')", name="ck_vote_option"),
    )
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False, index=True)
    client_hash = db.Column(db.String(64), nullable=False)
    request_id = db.Column(db.String(64), nullable=False, unique=True)
    option = db.Column(db.String(1), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Scorecard(db.Model):
    __tablename__ = "scorecard"
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("round.id"), nullable=False, unique=True)
    ratings_json = db.Column(db.Text, nullable=False, default="[]")
    note = db.Column(db.String(300))
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    @property
    def ratings(self):
        return json.loads(self.ratings_json or "[]")


class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    at = db.Column(db.DateTime, nullable=False, default=utcnow)
    actor = db.Column(db.String(20), nullable=False, default="system")
    action = db.Column(db.String(60), nullable=False)
    detail = db.Column(db.String(500))
