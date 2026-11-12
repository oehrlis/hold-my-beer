"""Konfiguration aus Umgebungsvariablen (Development, Testing, Production)."""
import os
from pathlib import Path

SESSION_TITLE = "Denn sie wissen nicht, was sie tun"
SESSION_SUBTITLE = "Oracle live mit Oehrli, Berger und KI"

DEV_ADMIN_PASSWORD = "oracle-dev"  # nur Development, siehe README
DEV_SECRET_KEY = "dev-only-secret-key-not-for-production"


def _bool(value, default):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def build_config(instance_path, overrides=None):
    env = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").lower()
    if overrides and "APP_ENV" in overrides:
        env = overrides["APP_ENV"]
    if env not in ("development", "testing", "production"):
        raise RuntimeError("APP_ENV muss development, testing oder production sein (ist: %r)" % env)

    default_db = "sqlite:///" + str(Path(instance_path) / "voting.db")
    cfg = {
        "APP_ENV": env,
        "SESSION_TITLE": SESSION_TITLE,
        "SESSION_SUBTITLE": SESSION_SUBTITLE,
        "SECRET_KEY": os.environ.get("SECRET_KEY") or None,
        "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD") or None,
        "PUBLIC_BASE_URL": (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/"),
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL") or default_db,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {"connect_args": {"timeout": 5}},
        "HOST": os.environ.get("HOST", "0.0.0.0"),
        "PORT": int(os.environ.get("PORT", "5000")),
        "PROXY_FIX_ENABLED": _bool(os.environ.get("PROXY_FIX_ENABLED"), False),
        "BACKUP_DIR": os.environ.get("BACKUP_DIR") or str(Path(instance_path).parent / "backups"),
        "MAX_CONTENT_LENGTH": 16 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "WTF_CSRF_TIME_LIMIT": None,
        "RATELIMIT_STORAGE_URI": "memory://",
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_HEADERS_ENABLED": False,
        "VOTE_RATE_LIMIT": "10 per minute",
        "LOGIN_RATE_LIMIT": "5 per minute;20 per hour",
        "STATE_CACHE_TTL": 0.5,
        "ADMIN_IDLE_SECONDS": 60 * 60,
        "CHALLENGE_SECONDS": 300,
        "AUTO_PUBLISH_RESULT": _bool(os.environ.get("AUTO_PUBLISH_RESULT"), True),
        "JSON_AS_ASCII": False,
    }

    if env == "production":
        cfg["SESSION_COOKIE_SECURE"] = _bool(os.environ.get("SESSION_COOKIE_SECURE"), True)
        missing = [k for k in ("SECRET_KEY", "ADMIN_PASSWORD") if not cfg[k]]
        if missing:
            raise RuntimeError("Production-Start verweigert, fehlende Variable(n): " + ", ".join(missing))
    else:
        cfg["SESSION_COOKIE_SECURE"] = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)
        cfg["SECRET_KEY"] = cfg["SECRET_KEY"] or DEV_SECRET_KEY
        cfg["ADMIN_PASSWORD"] = cfg["ADMIN_PASSWORD"] or DEV_ADMIN_PASSWORD
    if env == "testing":
        cfg["RATELIMIT_ENABLED"] = False
        cfg["STATE_CACHE_TTL"] = 0
        cfg["AUTO_PUBLISH_RESULT"] = False  # Tests pruefen den manuellen Pfad; Auto-Pfad hat eigene Tests

    cfg["DEBUG"] = False
    cfg["TESTING"] = env == "testing"
    if overrides:
        cfg.update(overrides)
    return cfg
