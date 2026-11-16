import hashlib
import logging
import sqlite3
from pathlib import Path

from flask import Flask, g, render_template, request
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .clientid import attach_cookie
from .config import build_config
from .extensions import csrf, db, limiter, migrate
from .util import ApiError, fail


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


QR_PATHS = ("/qr.svg", "/share-qr.svg")
NO_STORE_PATHS = QR_PATHS + ("/healthz", "/readyz")


def _apply_pool_format(app, overrides):
    """Uebernimmt voting_seconds/challenge_minutes aus der Pool-Datei (Seed meldet Pool-Fehler hart)."""
    from .pool import PoolError, load_pool
    try:
        fmt = load_pool(app.config["POOL_FILE"])["format"]
    except PoolError as e:
        app.logger.warning("WARNUNG: Pool-Format nicht geladen, Standardwerte (Voting %d s, Challenge %d s): %s",
                           app.config["VOTING_SECONDS"], app.config["CHALLENGE_SECONDS"], e)
        return
    if fmt["voting_seconds"] and "VOTING_SECONDS" not in overrides:
        app.config["VOTING_SECONDS"] = fmt["voting_seconds"]
    if fmt["challenge_minutes"] and "CHALLENGE_SECONDS" not in overrides:
        app.config["CHALLENGE_SECONDS"] = fmt["challenge_minutes"] * 60


def _wants_json():
    return request.path.startswith(("/api/", "/admin/api/")) or request.is_json


def create_app(overrides=None):
    app = Flask(__name__, instance_path=str(Path(__file__).resolve().parent.parent / "instance"))
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(build_config(app.instance_path, overrides))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if app.config["APP_ENV"] == "production" and app.config["PROXY_FIX_ENABLED"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXY_FIX_X_FOR"], x_proto=1, x_host=1, x_prefix=0)
    _apply_pool_format(app, overrides or {})

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from . import models  # noqa: F401
    from .blueprints import admin, api, public, screen
    for module in (public, screen, admin, api):
        app.register_blueprint(module.bp)

    from .cli import register_cli
    register_cli(app)

    # Cache-Busting: ?v=<Hash des Inhalts> an jeder static-URL. Statische Dateien werden 4 h gecacht - ohne das
    # behielt ein offener Beamer-Browser nach einem Deploy das alte JS (Bier-Roehre fehlte, 2026-11-16).
    versions = {}

    @app.url_defaults
    def _static_version(endpoint, values):
        name = values.get("filename") if endpoint == "static" else None
        if not name or "v" in values:
            return
        if name not in versions:
            try:
                versions[name] = hashlib.sha256((Path(app.static_folder) / name).read_bytes()).hexdigest()[:10]
            except OSError:
                versions[name] = None
        if versions[name]:
            values["v"] = versions[name]

    @app.context_processor
    def _theme_ctx():
        # Vorgabe fuers erste Rendern (kein Aufblitzen des anderen Layouts); danach kommt sie per Polling
        from .models import SessionState
        from .services.voting import theme_of
        try:
            ss = db.session.get(SessionState, 1)
        except Exception:  # DB nicht bereit: Fehlerseite trotzdem rendern
            db.session.rollback()
            ss = None
        return {"theme_default": theme_of(ss) if ss else app.config["APP_THEME"]}

    @app.after_request
    def headers(resp):
        attach_cookie(resp)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        # nichts Dynamisches darf in einem Proxy/CDN (Cloudflare) landen: JSON, HTML (CSRF-Token), QR-Codes
        if _wants_json() or resp.mimetype == "text/html" or request.path in NO_STORE_PATHS:
            resp.headers["Cache-Control"] = "no-store"
        if request.path in QR_PATHS:
            # nur die QR-Bilder duerfen fremde Seiten (Folien per file:// oder andere Origin) per <img> laden;
            # X-Frame-Options/frame-ancestors bleiben unveraendert, Einbetten als iframe bleibt verboten
            resp.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        if app.config["SESSION_COOKIE_SECURE"]:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        return resp

    def error_response(code, message, status):
        if _wants_json():
            return fail(code, message, status)
        return render_template("error.html", status=status, message=message), status

    @app.errorhandler(ApiError)
    def _api_error(e):
        db.session.rollback()
        return error_response(e.code, e.message, e.status)

    @app.errorhandler(CSRFError)
    def _csrf(e):
        return error_response("csrf_invalid", "Sicherheitstoken ungültig oder abgelaufen. Bitte Seite neu laden.", 400)

    @app.errorhandler(429)
    def _rate(e):
        return error_response("rate_limited", "Zu viele Anfragen. Bitte kurz warten.", 429)

    @app.errorhandler(HTTPException)
    def _http(e):
        msgs = {404: "Seite nicht gefunden.", 405: "Methode nicht erlaubt.", 413: "Anfrage zu gross."}
        return error_response("http_%d" % e.code, msgs.get(e.code, "Anfrage nicht möglich."), e.code)

    @app.errorhandler(Exception)
    def _unexpected(e):
        app.logger.exception("Unerwarteter Serverfehler")
        db.session.rollback()
        try:
            from .services.audit import audit
            audit("server_error", type(e).__name__, actor="system")
            db.session.commit()
        except Exception:
            db.session.rollback()
        return error_response("server_error", "Interner Fehler. Bitte erneut versuchen.", 500)

    return app
