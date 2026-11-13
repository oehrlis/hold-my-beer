"""Hinter dem Cloudflare Tunnel (HTTPS, ProxyFix) sendet der Browser wegen Referrer-Policy no-referrer
keinen Referer. Login und Stimmabgabe muessen trotzdem funktionieren; das CSRF-Token bleibt Pflicht."""
import re

from conftest import PASSWORD, make_app, open_round

HTTPS = {"base_url": "https://hmb.example.org"}


def _token(http, path="/"):
    html = http.get(path, **HTTPS).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def test_vote_over_https_without_referer(tmp_path):
    from conftest import Client
    app = make_app(tmp_path)
    admin = Client(app)
    assert admin.login().status_code == 302
    open_round(admin)
    http = app.test_client()
    tok = _token(http)
    http.get("/api/state", **HTTPS)
    r = http.post("/api/vote", json={"option": "A", "request_id": "https0001"},
                  headers={"X-CSRFToken": tok}, **HTTPS)
    assert r.status_code == 200, r.get_json()


def test_admin_login_over_https_without_referer(tmp_path):
    app = make_app(tmp_path)
    http = app.test_client()
    tok = _token(http, "/admin")
    r = http.post("/admin/login", data={"password": PASSWORD, "csrf_token": tok}, **HTTPS)
    assert r.status_code == 302


def test_csrf_token_still_required_over_https(tmp_path):
    app = make_app(tmp_path)
    http = app.test_client()
    http.get("/", **HTTPS)
    r = http.post("/api/vote", json={"option": "A", "request_id": "https0002"}, **HTTPS)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "csrf_invalid"
