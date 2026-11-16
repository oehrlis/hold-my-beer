from conftest import Client, PASSWORD
from votingapp.extensions import db
from votingapp.models import Round, RoundOption, Topic
from votingapp.services.seed import seed_data


def test_index_and_screen(client):
    r = client.get("/")
    assert r.status_code == 200 and "Denn sie wissen nicht, was sie tun" in r.get_data(as_text=True)
    assert 'src="/share-qr.svg"' in r.get_data(as_text=True)
    assert 'class="share-qr"' in r.get_data(as_text=True)
    s = client.get("/screen")
    assert s.status_code == 200 and 'src="/qr.svg"' in s.get_data(as_text=True)
    assert 'src="/share-qr.svg"' in s.get_data(as_text=True)
    q = client.get("/qr.svg")
    assert q.status_code == 200 and q.mimetype == "image/svg+xml" and b"<svg" in q.data
    share_qr = client.get("/share-qr.svg")
    assert share_qr.status_code == 200 and share_qr.mimetype == "image/svg+xml" and b"<svg" in share_qr.data


def test_admin_page_shows_login_without_session(client):
    r = client.get("/admin")
    assert r.status_code == 200 and "Admin-Anmeldung" in r.get_data(as_text=True)


def test_health_and_ready(client):
    assert client.get("/healthz").get_json()["ok"] is True
    r = client.get("/readyz")
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "ready"


def test_security_headers(client):
    r = client.get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_admin_login_ok_and_logout(client):
    assert client.login().status_code == 302
    assert client.get("/admin").status_code == 200
    assert "Abmelden" in client.get("/admin").get_data(as_text=True)
    client.http.post("/admin/logout", data={"csrf_token": client.csrf()})
    assert client.get("/admin/api/state").status_code == 401


def test_admin_login_wrong_password(client):
    r = client.login("falsch")
    assert r.status_code == 401
    assert client.get("/admin/api/state").status_code == 401


def test_unauthenticated_admin_rejected(client):
    assert client.get("/admin/api/state").status_code == 401
    r = client.admin("open_voting", {"duration": 30})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "unauthorized"


def test_csrf_enforced(app):
    c = Client(app)
    c.login()
    r = c.post("/admin/api/open_voting", {"duration": 30}, csrf=False)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "csrf_invalid"
    r = c.post("/api/vote", {"option": "A", "request_id": "abcdefgh"}, csrf=False)
    assert r.status_code == 400
    r = c.http.post("/admin/login", data={"password": PASSWORD})
    assert r.status_code == 400


def test_seed_data_complete_and_idempotent(app, admin):
    with app.app_context():
        assert Round.query.count() == 3 and RoundOption.query.count() == 9
        assert Topic.query.filter_by(is_reserve=True).count() == 13
        before = Topic.query.count()
    admin.admin("open_voting", {"duration": 30})
    c = Client(app)
    c.post("/api/vote", {"option": "B", "request_id": "seedtest-1"})
    with app.app_context():
        seed_data()
        seed_data()
        assert Topic.query.count() == before and Round.query.count() == 3
    assert admin.astate()["live"]["counts"]["B"] == 1


def test_migrations_create_schema(tmp_path):
    from flask_migrate import upgrade
    from sqlalchemy import inspect
    from votingapp import create_app
    app = create_app({"APP_ENV": "testing", "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "m.db")})
    with app.app_context():
        upgrade(directory="migrations")
        names = set(inspect(db.engine).get_table_names())
        assert {"vote", "round", "session_state", "scorecard", "audit_log"} <= names
        assert "theme" in {c["name"] for c in inspect(db.engine).get_columns("session_state")}
        seed_data()
    assert app.test_client().get("/readyz").status_code == 200


def test_production_requires_secrets(monkeypatch, tmp_path):
    import pytest
    from votingapp.config import build_config
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        build_config(str(tmp_path))
    monkeypatch.setenv("SECRET_KEY", "x")
    monkeypatch.setenv("ADMIN_PASSWORD", "y")
    cfg = build_config(str(tmp_path))
    assert cfg["SESSION_COOKIE_SECURE"] is True and cfg["DEBUG"] is False
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    assert build_config(str(tmp_path))["SESSION_COOKIE_SECURE"] is False


def test_sqlite_wal_enabled(app):
    from sqlalchemy import text
    with app.app_context():
        assert db.session.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert db.session.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_screen_burp_only_with_burp_file(app, client, tmp_path):
    assert client.get("/screen/burp").status_code == 404
    assert 'id="s-sound"' not in client.get("/screen").get_data(as_text=True)
    f = tmp_path / "burp.m4a"
    f.write_bytes(b"not really audio")
    app.config["BURP_FILE"] = str(f)
    page = client.get("/screen").get_data(as_text=True)
    assert 'id="s-sound"' in page and 'data-src="/screen/burp"' in page and "hoerspielbox.de" in page
    r = client.get("/screen/burp")
    assert r.status_code == 200 and r.data == b"not really audio"
    app.config["BURP_FILE"] = str(tmp_path / "missing.m4a")
    assert client.get("/screen/burp").status_code == 404
