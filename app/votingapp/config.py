"""Konfiguration aus Umgebungsvariablen (Development, Testing, Production)."""
import os
from pathlib import Path

from .pool import DEFAULT_POOL_FILE

SESSION_TITLE = "Denn sie wissen nicht, was sie tun"
SESSION_SUBTITLE = "Oracle live mit Oehrli, Berger und KI"

THEMES = ("acn", "hmb")  # Accenture | Hold my Beer (OraDBA) - gleiche Kuerzel wie das Deck (slides/deck-theme.js)

DEV_ADMIN_PASSWORD = "oracle-dev"  # nur Development, siehe README
DEV_SECRET_KEY = "dev-only-secret-key-not-for-production"


def _bool(value, default):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _int(value, default, name, lo, hi):
    if value is None or value == "":
        return default
    try:
        n = int(value)
    except ValueError:
        n = None
    if n is None or not lo <= n <= hi:
        raise RuntimeError("%s muss eine ganze Zahl von %d bis %d sein (ist: %r)" % (name, lo, hi, value))
    return n


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
        # Anzahl vertrauenswuerdiger Proxies, die X-Forwarded-For anhaengen (Cloudflare Tunnel: 1,
        # Cloudflare + Nginx mit $proxy_add_x_forwarded_for: 2). Proto/Host kommen immer vom letzten Hop.
        "PROXY_FIX_X_FOR": _int(os.environ.get("PROXY_FIX_X_FOR"), 1, "PROXY_FIX_X_FOR", 1, 5),
        # Ziel des Teilen-QR-Codes (Icon oben rechts); leer = PUBLIC_BASE_URL bzw. lokale Adresse
        # Layout-Vorgabe, bis der Admin eine andere waehlt; jeder Client kann lokal abweichen (?theme=, Taste T)
        "APP_THEME": (os.environ.get("APP_THEME") or "acn").strip().lower(),
        "SHARE_URL": (os.environ.get("SHARE_URL") or "").rstrip("/"),
        # Themenpool (YAML); relativ = ab App-Verzeichnis. Siehe README "Pool-Datei".
        "POOL_FILE": os.environ.get("POOL_FILE") or DEFAULT_POOL_FILE,
        "BACKUP_DIR": os.environ.get("BACKUP_DIR") or str(Path(instance_path).parent / "backups"),
        "MAX_CONTENT_LENGTH": 16 * 1024,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "WTF_CSRF_TIME_LIMIT": None,
        # Kein Referer-Abgleich bei HTTPS: die App sendet Referrer-Policy no-referrer, der Browser schickt also
        # keinen Referer, und Flask-WTF lehnte hinter dem Tunnel jeden POST ab (Login, Stimme). Schutz bleibt
        # das sessiongebundene, signierte Token plus SameSite=Lax (2026-11-13).
        "WTF_CSRF_SSL_STRICT": False,
        "RATELIMIT_STORAGE_URI": "memory://",
        "RATELIMIT_ENABLED": True,
        "RATELIMIT_HEADERS_ENABLED": False,
        "VOTE_RATE_LIMIT": "10 per minute",
        "LOGIN_RATE_LIMIT": "5 per minute;20 per hour",
        "STATE_CACHE_TTL": 0.5,
        "ADMIN_IDLE_SECONDS": 60 * 60,
        "CHALLENGE_SECONDS": 300,  # wird beim App-Start aus format.challenge_minutes des Pools gesetzt
        "VOTING_SECONDS": 60,  # Vorauswahl im Admin; aus format.voting_seconds des Pools
        "AUTO_PUBLISH_RESULT": _bool(os.environ.get("AUTO_PUBLISH_RESULT"), True),
        "JSON_AS_ASCII": False,
    }

    if cfg["APP_THEME"] not in THEMES:
        raise RuntimeError("APP_THEME muss %s sein (ist: %r)" % (" oder ".join(THEMES), cfg["APP_THEME"]))

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
