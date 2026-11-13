"""Layout Accenture (acn) / Hold my Beer (hmb): Vorgabe aus APP_THEME, Admin setzt sie fuer alle."""
import re

import pytest

from conftest import Client, make_app


def _html_theme(client, path="/"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'<html[^>]*data-theme-default="([a-z]+)"', html).group(1)


def test_default_theme_from_config(client):
    assert client.state()["theme"] == "acn"
    assert _html_theme(client) == "acn"
    assert _html_theme(client, "/screen") == "acn"


def test_app_theme_env(tmp_path):
    c = Client(make_app(tmp_path, APP_THEME="hmb"))
    assert c.state()["theme"] == "hmb"
    assert _html_theme(c, "/admin") == "hmb"  # auch die Login-Seite


def test_invalid_app_theme_rejected(monkeypatch, tmp_path):
    from votingapp.config import build_config
    monkeypatch.setenv("APP_THEME", "pink")
    with pytest.raises(RuntimeError):
        build_config(str(tmp_path))


def test_admin_sets_theme_for_everyone(admin, client):
    r = admin.admin("set_theme", {"theme": "hmb"})
    assert r.status_code == 200 and r.get_json()["data"]["theme"] == "hmb"
    assert client.state()["theme"] == "hmb"
    assert _html_theme(client) == "hmb"
    assert any(a["action"] == "theme_set" and a["detail"] == "hmb" for a in admin.astate()["audit"])
    # gleiche Wahl erneut: kein zweiter Auditeintrag
    admin.admin("set_theme", {"theme": "hmb"})
    assert sum(a["action"] == "theme_set" for a in admin.astate()["audit"]) == 1


def test_theme_survives_session_reset(admin, client):
    admin.admin("set_theme", {"theme": "hmb"})
    assert admin.admin("reset_session", {"confirm": "RESET"}).status_code == 200
    assert client.state()["theme"] == "hmb"


def test_set_theme_validation_and_auth(admin, client):
    assert admin.admin("set_theme", {"theme": "pink"}).status_code == 400
    assert admin.admin("set_theme", {}).status_code == 400
    assert client.admin("set_theme", {"theme": "hmb"}).status_code == 401
    assert client.state()["theme"] == "acn"


def test_static_assets(client):
    assert client.get("/static/js/theme.js").status_code == 200
    svg = client.get("/static/img/hold-my-beer.svg")
    assert svg.status_code == 200 and svg.mimetype == "image/svg+xml"
