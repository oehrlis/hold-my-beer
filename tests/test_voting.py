import threading
from datetime import timedelta

from conftest import Client, expire_voting, make_app, new_clients, open_round, play_to_result
from votingapp.extensions import db
from votingapp.models import AuditLog, SessionState, Vote
from votingapp.util import utcnow


def vote(c, opt, rid=None):
    return c.post("/api/vote", {"option": opt, "request_id": rid or ("req-" + opt + "-" + c.cid()[:12])})


def test_open_vote_and_state(admin, client):
    assert client.state()["state"] == "waiting"
    open_round(admin, 45)
    s = client.state()
    assert s["state"] == "voting_open" and s["round"]["number"] == 1 and len(s["round"]["options"]) == 3
    assert 0 < s["voting"]["remaining"] <= 45


def test_vote_saved_and_double_rejected(admin, client):
    open_round(admin)
    r = vote(client, "A")
    assert r.status_code == 200 and r.get_json()["data"]["option"] == "A"
    assert client.state()["my_vote"] == "A"
    r2 = client.post("/api/vote", {"option": "B", "request_id": "another-request-id"})
    assert r2.status_code == 409 and r2.get_json()["error"]["code"] == "already_voted"
    assert admin.astate()["live"]["counts"] == {"A": 1, "B": 0, "C": 0, "D": 0}


def test_retry_with_same_request_id_is_idempotent(admin, client):
    open_round(admin)
    assert vote(client, "C", "retry-123456").status_code == 200
    r = vote(client, "C", "retry-123456")
    assert r.status_code == 200 and r.get_json()["data"]["repeated"] is True
    assert admin.astate()["live"]["total"] == 1


def test_other_client_may_vote(admin, app):
    open_round(admin)
    a, b = new_clients(app, 2)
    assert vote(a, "A").status_code == 200 and vote(b, "A").status_code == 200
    assert admin.astate()["live"]["counts"]["A"] == 2


def test_invalid_input(admin, client):
    open_round(admin)
    assert client.post("/api/vote", {"option": "Z", "request_id": "abcdefgh"}).status_code == 400
    assert client.post("/api/vote", {"option": "A", "request_id": "x"}).status_code == 400
    assert client.post("/api/vote", {"option": "A"}).status_code == 400


def test_vote_rejected_when_not_open(client):
    r = vote(client, "A")
    assert r.status_code == 403 and r.get_json()["error"]["code"] == "voting_closed"


def test_same_client_in_other_round_allowed(admin, client):
    open_round(admin)
    assert vote(client, "A").status_code == 200
    admin.admin("close_voting"); admin.admin("publish_result")
    admin.admin("select_challenge", {"option": "A"}); admin.admin("start_challenge")
    admin.admin("finish_challenge"); assert admin.admin("next_round").status_code == 200
    open_round(admin)
    assert client.state()["round"]["number"] == 2 and client.state()["my_vote"] is None
    assert vote(client, "B", "round2-request-1").status_code == 200


def test_parallel_double_vote_counts_once(admin, app):
    open_round(admin)
    c = Client(app)
    cookie = c.cid()
    clients = []
    for i in range(12):
        x = Client(app)
        x.http.set_cookie("olv_cid", cookie)
        clients.append(x)
        x.csrf()
    results = []
    barrier = threading.Barrier(len(clients))

    def go(i, x):
        barrier.wait()
        results.append(x.post("/api/vote", {"option": "ABC"[i % 3], "request_id": "parallel-req-%d" % i}).status_code)

    ts = [threading.Thread(target=go, args=(i, x)) for i, x in enumerate(clients)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(results).count(200) == 1 and results.count(409) == 11
    with app.app_context():
        assert Vote.query.count() == 1


def test_no_intermediate_results_for_participants(admin, app, client):
    open_round(admin)
    for opt in "AAB":
        vote(Client(app), opt)
    body = client.get("/api/state").get_data(as_text=True)
    s = client.state()
    assert s["result"] is None and s["voting"]["votes"] == 3
    assert '"counts"' not in body and '"tally"' not in body
    assert admin.astate()["live"]["counts"] == {"A": 2, "B": 1, "C": 0, "D": 0}


def test_server_side_timer_and_late_vote(admin, app, client):
    open_round(admin, 30)
    expire_voting(app)
    r = vote(client, "A")
    assert r.status_code == 403
    assert client.state()["state"] == "voting_closed"  # automatisch geschlossen
    assert client.state()["result"] is None  # Ergebnis bleibt verborgen
    with app.app_context():
        ss = db.session.get(SessionState, 1)
        assert ss.voting_started_at and ss.voting_ends_at
        assert AuditLog.query.filter_by(action="voting_closed", actor="system").count() == 1


def test_duration_validation(admin):
    assert admin.admin("open_voting", {"duration": 1}).status_code == 400
    assert admin.admin("open_voting", {"duration": "abc"}).status_code == 400


def test_winner_calculation(admin):
    play_to_result(admin, ["B", "B", "A"])
    s = admin.astate()
    assert s["state"] == "result_visible"
    assert s["result"]["winner"] == "B" and not s["result"]["tie"] and s["result"]["counts"] == {"A": 1, "B": 2, "C": 0, "D": 0}
    assert s["live"]["runner_up"] == "A"


def test_tie_has_no_random_winner(admin):
    play_to_result(admin, ["A", "B"])
    r = admin.astate()["result"]
    assert r["tie"] is True and r["winner"] is None and r["tied"] == ["A", "B"]
    assert admin.admin("start_challenge").status_code == 409  # kein Gewinner, nichts gewaehlt


def test_runoff_after_tie(admin, app):
    open_round(admin)
    for opt in "AB":
        vote(Client(app), opt)
    admin.admin("close_voting")
    assert admin.admin("runoff", {"duration": 30}).status_code == 400  # Bestaetigung fehlt
    assert admin.admin("runoff", {"confirm": True, "duration": 30}).status_code == 200
    s = Client(app).state()
    assert s["state"] == "voting_open" and s["round"]["active"] == ["A", "B"] and s["voting"]["votes"] == 0
    c = Client(app)
    assert c.post("/api/vote", {"option": "C", "request_id": "runoff-req-1"}).status_code == 400


def test_manual_challenge_keeps_real_winner(admin):
    play_to_result(admin, ["A", "A", "B"])
    assert admin.admin("select_challenge", {"option": "C"}).status_code == 400  # Begruendung fehlt
    r = admin.admin("select_challenge", {"option": "C", "reason": "Zeit knapp, C ist schneller"})
    assert r.status_code == 200
    s = admin.astate()
    assert s["result"]["winner"] == "A" and s["result"]["selected"] == "C"
    assert s["result"]["deviation_reason"].startswith("Zeit")
    assert s["result"]["counts"]["A"] == 2
    assert admin.admin("start_challenge").status_code == 200
    assert admin.astate()["challenge"]["key"] == "C"


def test_challenge_defaults_to_winner(admin):
    play_to_result(admin, ["C", "C", "A"])
    assert admin.admin("start_challenge").status_code == 200
    s = admin.astate()
    assert s["state"] == "challenge_running" and s["challenge"]["key"] == "C"
    assert 295 < s["challenge"]["remaining"] <= 300


def test_state_transitions_and_409(admin):
    for action in ("close_voting", "publish_result", "start_challenge", "finish_challenge", "next_round", "show_closing"):
        r = admin.admin(action)
        assert r.status_code == 409 and r.get_json()["error"]["code"] == "invalid_transition", action
    open_round(admin)
    assert admin.admin("open_voting", {"duration": 30}).status_code == 409
    assert admin.admin("publish_result").status_code == 409
    assert admin.admin("activate_round", {"round_id": 2}).status_code == 409


def test_scorecard(admin):
    play_to_result(admin, ["A"])
    admin.admin("start_challenge")
    assert admin.admin("save_scorecard", {"ratings": ["ai_correct"]}).status_code == 409
    admin.admin("finish_challenge")
    assert admin.admin("save_scorecard", {"ratings": ["nope"]}).status_code == 400
    r = admin.admin("save_scorecard", {"ratings": ["ai_halluziniert_x"], "note": "x"})
    assert r.status_code == 400
    r = admin.admin("save_scorecard", {"ratings": ["ai_hallucinated", "task_partial"], "note": "Listener nicht gefunden"})
    assert r.status_code == 200
    sc = admin.astate()["scorecard"]
    assert [x["label"] for x in sc["ratings"]] == ["AI halluziniert", "Aufgabe teilweise abgeschlossen"]
    assert sc["note"] == "Listener nicht gefunden"
    assert admin.admin("save_scorecard", {"ratings": [], "note": "y" * 301}).status_code == 400


def test_reset_round_and_session(admin, app):
    play_to_result(admin, ["A", "B", "B"])
    assert admin.admin("reset_round").status_code == 400  # ohne Bestaetigung
    assert admin.admin("reset_round", {"confirm": True}).status_code == 200
    s = admin.astate()
    assert s["state"] == "waiting" and s["live"]["total"] == 0 and s["result"] is None
    play_to_result(admin, ["C"])
    assert admin.admin("reset_session", {"confirm": True}).status_code == 400
    assert admin.admin("reset_session", {"confirm": "RESET"}).status_code == 200
    s = admin.astate()
    assert s["state"] == "waiting" and s["round"]["number"] == 1
    with app.app_context():
        assert Vote.query.count() == 0
        assert AuditLog.query.filter(AuditLog.action.in_(["reset_round", "reset_session"])).count() == 2


def test_reserve_topic_assignment(admin):
    s = admin.astate()
    rid, topic = s["rounds"][1]["id"], s["reserve"][0]
    r = admin.admin("assign_reserve", {"round_id": rid, "option": "C", "topic_id": topic["id"]})
    assert r.status_code == 200
    assert admin.astate()["rounds"][1]["options"][2]["title"] == topic["title"]
    assert admin.admin("assign_reserve", {"round_id": rid, "option": "C", "topic_id": 1}).status_code == 400


def test_audit_log_contents(admin, app):
    open_round(admin)
    Client(app).login("geheim-xyz-123")
    with app.app_context():
        actions = [a.action for a in AuditLog.query.all()]
        assert {"admin_login", "voting_opened", "admin_login_failed"} <= set(actions)
        details = " ".join((a.detail or "") for a in AuditLog.query.all())
        assert "test-admin-pw" not in details and "geheim-xyz-123" not in details


def test_persistence_across_restart(admin, app, tmp_path):
    play_to_result(admin, ["B", "B", "C"])
    admin.admin("select_challenge", {"option": "B"})
    admin.admin("start_challenge")
    app2 = make_app(tmp_path)  # "Neustart": neue App-Instanz, gleiche SQLite-Datei
    c = Client(app2)
    s = c.state()
    assert s["state"] == "challenge_running" and s["result"]["counts"]["B"] == 2
    assert s["challenge"]["key"] == "B" and s["challenge"]["remaining"] > 0
    c2 = Client(app2); c2.login()
    assert c2.astate()["live"]["total"] == 3


def test_rate_limits(tmp_path):
    app = make_app(tmp_path, RATELIMIT_ENABLED=True, VOTE_RATE_LIMIT="3 per minute")
    c = Client(app)
    codes = [c.http.post("/admin/login", data={"password": "x", "csrf_token": c.csrf()}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    v = Client(app)
    codes = [v.post("/api/vote", {"option": "A", "request_id": "rate-limit-%d" % i}).status_code for i in range(6)]
    # erster Request ohne Cookie zaehlt im IP-Bucket, danach pro Client-ID
    assert codes[:3] == [403] * 3 and codes[-2:] == [429, 429] and codes.count(403) <= 4
    assert v.post("/api/vote", {"option": "A", "request_id": "rate-limit-9"}).get_json()["error"]["code"] == "rate_limited"
    assert Client(app).get("/api/state").status_code == 200  # Polling nicht begrenzt


def test_request_size_limit(client):
    r = client.http.post("/api/vote", data=b"x" * 40000, headers={"X-CSRFToken": client.csrf(), "Content-Type": "application/json"})
    assert r.status_code == 413 and r.get_json()["ok"] is False


def test_admin_session_idle_timeout(app):
    c = Client(app)
    c.login()
    assert c.get("/admin/api/state").status_code == 200
    with c.http.session_transaction() as sess:
        sess["admin_seen"] -= 3601
    assert c.get("/admin/api/state").status_code == 401


def test_export_and_backup(admin, app, tmp_path):
    play_to_result(admin, ["A", "A"])
    from votingapp.services.backup import backup_database, export_data
    with app.app_context():
        data = export_data()
        assert data["rounds"][0]["result"]["tally"]["A"] == 2 and len(data["rounds"][0]["votes"]) == 2
        target = backup_database(tmp_path / "bk")
    import sqlite3
    assert sqlite3.connect(str(target)).execute("select count(*) from vote").fetchone()[0] == 2


def test_quick_reset_needs_password(admin, app, client):
    play_to_result(admin, ["A"])
    assert client.post("/admin/quick-reset", {"password": "nope", "scope": "round"}).status_code == 401
    assert admin.astate()["state"] == "result_visible"
    assert client.post("/admin/quick-reset", {"password": "test-admin-pw", "scope": "bogus"}).status_code == 400
    assert client.post("/admin/quick-reset", {"password": "test-admin-pw", "scope": "session"}).status_code == 200
    assert client.state()["state"] == "waiting" and admin.astate()["live"]["total"] == 0
    assert client.post("/admin/quick-reset", {"scope": "round"}, csrf=False).status_code == 400


def test_auto_publish_after_expiry_then_challenge_timer(tmp_path):
    app = make_app(tmp_path, AUTO_PUBLISH_RESULT=True)
    admin = Client(app); admin.login()
    open_round(admin, 30)
    for opt in "BBA":
        vote(Client(app), opt)
    expire_voting(app)
    s = Client(app).state()  # reiner Poll loest Schliessen + Freigabe aus
    assert s["state"] == "result_visible" and s["result"]["winner"] == "B"
    assert admin.admin("start_challenge").status_code == 200
    s = Client(app).state()
    assert s["state"] == "challenge_running" and s["challenge"]["key"] == "B"
    assert 295 < s["challenge"]["remaining"] <= 300
    with app.app_context():
        assert AuditLog.query.filter_by(action="result_published", actor="system").count() == 1


def test_manual_close_also_publishes_when_auto(tmp_path):
    app = make_app(tmp_path, AUTO_PUBLISH_RESULT=True)
    admin = Client(app); admin.login()
    open_round(admin)
    vote(Client(app), "C")
    assert admin.admin("close_voting").status_code == 200
    assert admin.astate()["state"] == "result_visible"


def _opt(admin, rid=None):
    s = admin.astate()
    rd = s["rounds"][0] if rid is None else next(r for r in s["rounds"] if r["id"] == rid)
    return rd["id"], rd["options"]


def test_edit_option_in_place_and_validation(admin):
    rid, opts = _opt(admin)
    ok = admin.admin("save_option", {"round_id": rid, "option": "A", "title": "Neuer Titel", "owner": "Martin",
                                     "category": "Betrieb", "difficulty": "Schwer", "risk": "Hoch"})
    assert ok.status_code == 200
    a = _opt(admin)[1][0]
    assert (a["title"], a["owner"], a["difficulty"], a["risk"]) == ("Neuer Titel", "Martin", "Schwer", "Hoch")
    base = {"round_id": rid, "option": "A", "title": "x"}
    assert admin.admin("save_option", {**base, "title": "  "}).status_code == 400
    assert admin.admin("save_option", {**base, "difficulty": "Extrem"}).status_code == 400
    assert admin.admin("save_option", {**base, "title": "y" * 201}).status_code == 400
    assert admin.admin("save_option", {**base, "title": _opt(admin)[1][1]["title"]}).status_code == 409  # Duplikat


def test_max_four_and_min_two_options(admin):
    rid, opts = _opt(admin)
    r = admin.admin("save_option", {"round_id": rid, "option": "new", "title": "Vierte Aufgabe"})
    assert r.status_code == 200 and [o["key"] for o in _opt(admin)[1]] == ["A", "B", "C", "D"]
    r = admin.admin("save_option", {"round_id": rid, "option": "new", "title": "Fuenfte Aufgabe"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "max_options"
    assert admin.admin("delete_option", {"round_id": rid, "option": "B"}).status_code == 200
    keys = [(o["key"], o["title"]) for o in _opt(admin)[1]]
    assert [k for k, _ in keys] == ["A", "B", "C"] and keys[2][1] == "Vierte Aufgabe"  # neu durchbuchstabiert
    assert admin.admin("delete_option", {"round_id": rid, "option": "A"}).status_code == 200
    r = admin.admin("delete_option", {"round_id": rid, "option": "A"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "min_options"


def test_vote_on_fourth_option_and_invalid_slot(admin, app):
    rid, _ = _opt(admin)
    admin.admin("save_option", {"round_id": rid, "option": "new", "title": "Vierte"})
    open_round(admin)
    s = Client(app).state()
    assert [o["key"] for o in s["round"]["options"]] == ["A", "B", "C", "D"]
    assert vote(Client(app), "D").status_code == 200
    assert admin.astate()["live"]["counts"]["D"] == 1
    # Runde 2 hat nur 3 Optionen: D ist dort ungueltig
    admin.admin("close_voting"); admin.admin("publish_result")
    admin.admin("select_challenge", {"option": "D"}); admin.admin("start_challenge"); admin.admin("finish_challenge")
    admin.admin("next_round"); open_round(admin)
    assert vote(Client(app), "D").status_code == 400


def test_edit_locked_when_not_waiting_or_played(admin, app):
    rid, _ = _opt(admin)
    open_round(admin)
    r = admin.admin("save_option", {"round_id": rid, "option": "A", "title": "Zu spaet"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "invalid_transition"
    vote(Client(app), "A")
    admin.admin("close_voting")
    assert admin.admin("delete_option", {"round_id": rid, "option": "C"}).status_code == 409


def test_reserve_topic_not_mutated_by_edit(admin):
    s = admin.astate()
    rid, topic = s["rounds"][1]["id"], s["reserve"][0]
    admin.admin("assign_reserve", {"round_id": rid, "option": "C", "topic_id": topic["id"]})
    r = admin.admin("save_option", {"round_id": rid, "option": "C", "title": "Eigene Version", "category": "X"})
    assert r.status_code == 200
    s = admin.astate()
    assert s["rounds"][1]["options"][2]["title"] == "Eigene Version"
    assert [t["title"] for t in s["reserve"]][0] == topic["title"]  # Reserve-Thema unveraendert
