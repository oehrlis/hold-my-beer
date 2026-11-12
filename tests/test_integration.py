"""Eine komplette Runde vom Login bis zum Closing, inklusive Neustart."""
from conftest import Client, PASSWORD, expire_voting, make_app


def test_full_session_flow(app, tmp_path):
    admin = Client(app)
    assert admin.login().status_code == 302                       # 1 Admin anmelden
    assert admin.admin("activate_round", {"round_id": admin.astate()["rounds"][0]["id"]}).status_code == 200  # 2
    assert admin.admin("open_voting", {"duration": 60}).status_code == 200  # 3
    clients = [Client(app) for _ in range(6)]
    picks = ["B", "B", "B", "A", "C", "B"]
    for c, p in zip(clients, picks):                              # 4 mehrere Clients stimmen ab
        assert c.post("/api/vote", {"option": p, "request_id": "flow-%s" % id(c)}).status_code == 200
    dup = clients[0].post("/api/vote", {"option": "A", "request_id": "flow-duplicate-1"})
    assert dup.status_code == 409                                  # 5 Doppelstimme
    assert clients[0].state()["result"] is None and clients[0].state()["voting"]["votes"] == 6  # 6
    expire_voting(app)                                             # 7 Timer ablaufen lassen
    late = Client(app).post("/api/vote", {"option": "A", "request_id": "flow-late-0001"})
    assert late.status_code == 403                                 # 8 spaete Stimme
    assert Client(app).state()["state"] == "voting_closed"
    assert admin.admin("publish_result").status_code == 200        # 9 Ergebnis freigeben
    screen = Client(app).state()                                   # 10 Beamer-Ergebnis
    assert screen["result"]["counts"] == {"A": 1, "B": 4, "C": 1, "D": 0} and screen["result"]["winner"] == "B"
    assert admin.admin("start_challenge").status_code == 200       # 11 Challenge-Timer
    assert admin.admin("finish_challenge").status_code == 200
    assert admin.admin("save_scorecard", {"ratings": ["human_with_ai", "task_done"], "note": "lief"}).status_code == 200  # 12

    app2 = make_app(tmp_path)                                      # 13 Neustart
    a2 = Client(app2); a2.login()
    s = a2.astate()                                                # 14 persistierter Zustand
    assert s["state"] == "scorecard_visible" and s["result"]["winner"] == "B"
    assert s["scorecard"]["note"] == "lief" and s["live"]["total"] == 6

    assert a2.admin("next_round").status_code == 200               # 15 naechste Runde
    assert a2.astate()["round"]["number"] == 2
    for n in (2, 3, 4):                                            # restliche Runden schnell durchspielen
        assert a2.admin("open_voting", {"duration": 30}).status_code == 200
        Client(app2).post("/api/vote", {"option": "A", "request_id": "flow-round-%d-xx" % n})
        for act in ("close_voting", "publish_result", "start_challenge", "finish_challenge"):
            assert a2.admin(act).status_code == 200
        if n < 4:
            assert a2.admin("next_round").status_code == 200
    assert a2.admin("next_round").status_code == 409               # keine 5. Runde
    assert a2.admin("show_closing").status_code == 200             # 16 Closing
    closing = Client(app2).state()
    assert closing["state"] == "closing" and len(closing["closing"]) == 4
    assert closing["closing"][0]["topic"] == "Shell Health-Check für Alert-Log und Listener"
