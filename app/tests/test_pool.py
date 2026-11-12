"""Seed aus der Pool-Datei, Format-Uebernahme, QR-Header fuer Folien, Proxy-Konfiguration."""
import textwrap

import pytest

from conftest import Client, make_app, play_to_result
from votingapp import create_app
from votingapp.extensions import db
from votingapp.models import Round, RoundOption, SessionState, Topic, Vote
from votingapp.pool import PoolError, load_pool, resolve_pool_path
from votingapp.services.seed import reset_slots, seed_data

POOL = textwrap.dedent("""\
    schema: 1
    event: {name: Test, short: T}
    format:
      voting_seconds: 45
      challenge_minutes: 3
      scorecard: [AI richtig, AI halluziniert, Falsches Problem gelöst, DBA-Instinkt gewinnt]
    rounds:
      - number: 1
        name: Eins
        options:
          - {key: A, title: Thema 1A, owner: Stefan, category: Security, difficulty: Leicht, risk: Niedrig, ai_pitfall: x}
          - {key: B, title: Thema 1B, owner: Martin, category: Betrieb, difficulty: Mittel, risk: Mittel}
          - {key: C, title: Thema 1C, owner: Gemeinsam, category: Betrieb, difficulty: Schwer, risk: Hoch}
      - number: 2
        name: Zwei
        options:
          - {key: A, title: Thema 2A, owner: Stefan, category: Security}
          - {key: B, title: Thema 2B, owner: Martin, category: Betrieb}
          - {key: C, title: Thema 2C, owner: Gemeinsam, category: OEM}
      - number: 3
        name: Drei
        options:
          - {key: A, title: Thema 3A}
          - {key: B, title: Thema 3B}
          - {key: C, title: Thema 3C}
    reserve:
      - {title: Reserve 1, owner: Stefan, category: OCI}
      - {title: Reserve 2, owner: Martin, category: Automation}
    """)


def write(tmp_path, text, name="pool.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


@pytest.fixture
def pool_app(tmp_path):
    return make_app(tmp_path, POOL_FILE=write(tmp_path, POOL))


def test_repo_pool_is_valid():
    pool = load_pool()  # Standard ../pool/doag-ak-2026.yaml
    assert [r["number"] for r in pool["rounds"]] == [1, 2, 3]
    assert all(len(r["options"]) == 3 for r in pool["rounds"]) and len(pool["reserve"]) == 12
    assert pool["format"]["voting_seconds"] == 60 and pool["format"]["challenge_minutes"] == 5


def test_seed_from_pool_file(pool_app):
    with pool_app.app_context():
        assert [r.name for r in Round.query.order_by(Round.number)] == ["Eins", "Zwei", "Drei"]
        assert RoundOption.query.count() == 9
        res = {t.title: t for t in Topic.query.filter_by(is_reserve=True)}
        assert set(res) == {"Reserve 1", "Reserve 2"} and res["Reserve 2"].owner == "Martin"
        t = Topic.query.filter_by(title="Thema 1C").one()
        assert (t.owner, t.difficulty, t.risk, t.is_reserve) == ("Gemeinsam", "Schwer", "Hoch", False)
        assert db.session.get(SessionState, 1).active_round.number == 1
    s = Client(pool_app).state()
    assert [o["key"] for o in s["round"]["options"]] == ["A", "B", "C"] and s["round"]["total"] == 3


def test_seed_idempotent_keeps_votes_and_edits(pool_app):
    admin = Client(pool_app)
    admin.login()
    play_to_result(admin, ["B", "B", "A"])
    with pool_app.app_context():
        before = (Topic.query.count(), RoundOption.query.count(), Round.query.count())
        rep1, rep2 = seed_data(), seed_data()
        assert (Topic.query.count(), RoundOption.query.count(), Round.query.count()) == before
        assert Vote.query.count() == 3 and rep1["warnings"] == rep2["warnings"] == []
    assert admin.astate()["result"]["counts"]["B"] == 2


def test_three_options_vote_and_reject_d(pool_app):
    admin = Client(pool_app)
    admin.login()
    assert admin.admin("open_voting", {"duration": 30}).status_code == 200
    c = Client(pool_app)
    assert c.post("/api/vote", {"option": "C", "request_id": "three-opt-1"}).status_code == 200
    r = Client(pool_app).post("/api/vote", {"option": "D", "request_id": "three-opt-2"})
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "invalid_option"


def test_missing_pool_file_errors(tmp_path):
    missing = str(tmp_path / "nope.yaml")
    with pytest.raises(PoolError, match="nicht gefunden: .*nope.yaml"):
        load_pool(missing)
    app = create_app({"APP_ENV": "testing", "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "x.db"),
                      "POOL_FILE": missing})
    with app.app_context():
        db.create_all()
        with pytest.raises(PoolError):
            seed_data()
        assert Round.query.count() == 0  # kein stiller Rueckfall auf eingebaute Daten
    result = app.test_cli_runner().invoke(args=["seed-data"])
    assert result.exit_code != 0 and "Pool-Datei nicht gefunden" in result.output


def test_cli_seed_with_pool_option(tmp_path):
    app = create_app({"APP_ENV": "testing", "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "c.db"),
                      "POOL_FILE": str(tmp_path / "unused.yaml")})
    with app.app_context():
        db.create_all()
    result = app.test_cli_runner().invoke(args=["seed-data", "--pool", write(tmp_path, POOL)])
    assert result.exit_code == 0, result.output
    assert "3 Runden, 9 Optionen, 2 Reserve-Themen" in result.output


@pytest.mark.parametrize("old,new,msg", [
    ("key: C, title: Thema 1C", "key: D, title: Thema 1C", "erwartet 'C'"),
    ("difficulty: Schwer", "difficulty: Extrem", "difficulty 'Extrem' ungueltig"),
    ("title: Thema 2C", "title: Thema 2B", "doppelt"),
    ("title: Reserve 2", "title: Thema 3A", "doppelt"),
    ("DBA-Instinkt gewinnt", "Zufall", "Scorecard-Kategorie"),
    ("schema: 1", "schema: 2", "schema: 1"),
    ("challenge_minutes: 3", "challenge_minutes: 0", "challenge_minutes"),
    ("number: 3", "number: 2", "Rundennummer 2 doppelt"),
])
def test_invalid_pool_rejected(tmp_path, old, new, msg):
    assert old in POOL
    path = write(tmp_path, POOL.replace(old, new, 1))
    app = create_app({"APP_ENV": "testing", "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "i.db")})
    with app.app_context():
        db.create_all()
        with pytest.raises(PoolError, match=msg):
            seed_data(path)


def test_empty_rounds_rejected():
    from votingapp.pool import parse_pool
    with pytest.raises(PoolError, match="'rounds' fehlt"):
        parse_pool({"schema": 1, "rounds": []})


def test_broken_yaml_rejected(tmp_path):
    with pytest.raises(PoolError, match="nicht lesbar"):
        load_pool(write(tmp_path, "rounds: [\n  - {number: 1"))


def test_relative_pool_path_is_app_root_based():
    assert resolve_pool_path("../pool/doag-ak-2026.yaml").name == "doag-ak-2026.yaml"
    assert resolve_pool_path("../pool/doag-ak-2026.yaml").is_file()


def test_old_round_4_warned_then_removed_on_session_reset(pool_app):
    with pool_app.app_context():
        t = Topic(title="Alt 4A")
        r4 = Round(number=4, name="Bruchstelle")
        db.session.add_all([t, r4])
        db.session.flush()
        db.session.add_all([RoundOption(round_id=r4.id, option=k, topic_id=t.id if k == "A" else
                                        Topic.query.filter_by(title="Thema 3%s" % k).one().id) for k in "AB"])
        db.session.get(Round, 1).name = "Warm-up alt"
        db.session.commit()
        warnings = seed_data()["warnings"]
        assert any("Runde 4 'Bruchstelle' steht nicht im Pool" in w for w in warnings)
        assert any("Runde 1 heisst in der DB 'Warm-up alt'" in w for w in warnings)
        assert Round.query.count() == 4  # seed loescht nie
    admin = Client(pool_app)
    admin.login()
    assert admin.admin("reset_session", {"confirm": "RESET"}).status_code == 200
    s = admin.astate()
    assert [r["name"] for r in s["rounds"]] == ["Eins", "Zwei", "Drei"] and s["round"]["number"] == 1


def test_reset_slots_keeps_round_with_votes(pool_app):
    with pool_app.app_context():
        r4 = Round(number=4, name="Alt")
        db.session.add(r4)
        db.session.flush()
        db.session.add(Vote(round_id=r4.id, client_hash="h" * 64, request_id="keep-vote-1", option="A"))
        db.session.commit()
        reset_slots()
        assert db.session.get(Round, r4.id) is not None and Vote.query.count() == 1


def test_pool_format_wired(pool_app, tmp_path):
    assert pool_app.config["CHALLENGE_SECONDS"] == 180 and pool_app.config["VOTING_SECONDS"] == 45
    admin = Client(pool_app)
    admin.login()
    assert "<option selected>45</option>" in admin.get("/admin").get_data(as_text=True)
    labels = [x["label"] for x in admin.astate()["ratings"]][:4]
    assert labels == ["AI richtig", "AI halluziniert", "Falsches Problem gelöst", "DBA-Instinkt gewinnt"]
    # explizite Konfiguration gewinnt gegen den Pool
    (tmp_path / "second").mkdir()
    app2 = make_app(tmp_path / "second", POOL_FILE=str(tmp_path / "pool.yaml"), CHALLENGE_SECONDS=42)
    assert app2.config["CHALLENGE_SECONDS"] == 42


def test_qr_cross_origin_embeddable(client):
    for path in ("/qr.svg", "/share-qr.svg"):
        r = client.get(path)
        assert r.status_code == 200 and r.mimetype == "image/svg+xml"
        assert r.headers["Cross-Origin-Resource-Policy"] == "cross-origin"
        assert r.headers["Cache-Control"] == "no-store"
        assert r.headers["X-Frame-Options"] == "DENY"  # iframe-Einbettung bleibt verboten
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    page = client.get("/")
    assert "Cross-Origin-Resource-Policy" not in page.headers


def test_no_store_for_html_and_state(client):
    for path in ("/", "/screen", "/admin", "/api/state"):
        assert client.get(path).headers["Cache-Control"] == "no-store", path


def test_share_url_configurable(tmp_path):
    app = make_app(tmp_path, SHARE_URL="https://voting.example.org")
    html = Client(app).get("/").get_data(as_text=True)
    assert 'href="https://voting.example.org/"' in html


def test_proxy_fix_hops_configurable(monkeypatch, tmp_path):
    from werkzeug.middleware.proxy_fix import ProxyFix
    from votingapp.config import build_config
    monkeypatch.setenv("PROXY_FIX_X_FOR", "2")
    assert build_config(str(tmp_path))["PROXY_FIX_X_FOR"] == 2
    monkeypatch.setenv("PROXY_FIX_X_FOR", "zwei")
    with pytest.raises(RuntimeError):
        build_config(str(tmp_path))
    monkeypatch.delenv("PROXY_FIX_X_FOR")
    monkeypatch.setenv("SECRET_KEY", "s")
    monkeypatch.setenv("ADMIN_PASSWORD", "p")
    app = create_app({"APP_ENV": "production", "SECRET_KEY": "s", "ADMIN_PASSWORD": "p",
                      "PROXY_FIX_ENABLED": True, "PROXY_FIX_X_FOR": 2,
                      "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "p.db")})
    assert isinstance(app.wsgi_app, ProxyFix) and app.wsgi_app.x_for == 2

    seen = {}

    @app.get("/_ip")
    def _ip():
        from flask import request
        seen["ip"] = request.remote_addr
        return "ok"

    # Cloudflare haengt die Client-IP an, Nginx die Cloudflare-Edge: "gefaelscht, client, edge"
    app.test_client().get("/_ip", headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.7, 172.70.1.1"},
                          environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert seen["ip"] == "203.0.113.7"
