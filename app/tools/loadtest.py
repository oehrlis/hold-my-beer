#!/usr/bin/env python3
"""Lasttest: simuliert Teilnehmer mit Polling, parallelen Stimmen und Doppelstimmen.

Standardmaessig NUR gegen localhost. Fuer einen anderen Host muss --allow-remote gesetzt werden.
Die Ziel-App muss mit Dev-Passwort laufen (oder --password), da der Test ein Voting oeffnet und
nach dem Test die Runde zuruecksetzt (reset_round).

  python tools/loadtest.py --base http://127.0.0.1:5000 --clients 150
"""
import argparse
import re
import statistics
import sys
import threading
import time
import uuid
from http.cookiejar import CookieJar
from urllib.parse import urlparse
import json
import urllib.request


class Session:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        self.token = None

    def req(self, method, path, body=None, form=None):
        data, headers = None, {}
        if body is not None:
            data = json.dumps(body).encode(); headers = {"Content-Type": "application/json", "X-CSRFToken": self.token or ""}
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
        r = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        t = time.perf_counter()
        try:
            with self.opener.open(r, timeout=20) as resp:
                raw, status = resp.read(), resp.status
        except urllib.error.HTTPError as e:
            raw, status = e.read(), e.code
        except Exception as e:  # Timeout, Verbindungsfehler
            return 0, str(e), time.perf_counter() - t
        return status, raw, time.perf_counter() - t

    def load_token(self):
        status, raw, _ = self.req("GET", "/")
        self.token = re.search(rb'name="csrf-token" content="([^"]+)"', raw).group(1).decode()


def pct(values, p):
    return sorted(values)[min(len(values) - 1, int(len(values) * p))] if values else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--clients", type=int, default=150)
    ap.add_argument("--password", default="oracle-dev")
    ap.add_argument("--polls", type=int, default=5, help="Statusabfragen pro Client vor/nach dem Voting")
    ap.add_argument("--allow-remote", action="store_true", help="Test gegen nicht-lokalen Host ausdruecklich erlauben")
    a = ap.parse_args()
    host = urlparse(a.base).hostname
    if host not in ("127.0.0.1", "localhost", "::1") and not a.allow_remote:
        sys.exit("Abbruch: %s ist nicht lokal. Nur mit --allow-remote erlaubt." % host)

    lat = {"state": [], "vote": []}
    codes = {}
    lock = threading.Lock()

    def rec(kind, status, dt):
        with lock:
            lat[kind].append(dt); codes[(kind, status)] = codes.get((kind, status), 0) + 1

    admin = Session(a.base); admin.load_token()
    admin.req("POST", "/admin/login", form={"password": a.password, "csrf_token": admin.token})
    admin.load_token()
    st, raw, _ = admin.req("POST", "/admin/api/reset_round", {"confirm": True})
    if st != 200:
        sys.exit("Admin-Login/Reset fehlgeschlagen (HTTP %s). Passwort pruefen (--password)." % st)
    st, raw, _ = admin.req("POST", "/admin/api/open_voting", {"duration": 120})
    if st != 200:
        sys.exit("Voting konnte nicht geoeffnet werden: %s" % raw[:200])

    sessions = [Session(a.base) for _ in range(a.clients)]
    for s in sessions: s.load_token()

    def poll_phase(s):
        for _ in range(a.polls):
            st, _, dt = s.req("GET", "/api/state"); rec("state", st, dt); time.sleep(0.05)

    def run(fn):
        ts = [threading.Thread(target=fn, args=(s,)) for s in sessions]
        [t.start() for t in ts]; [t.join() for t in ts]

    print("Phase 1: %d Clients pollen /api/state" % a.clients); run(poll_phase)

    expected = {"A": 0, "B": 0, "C": 0}
    plan = {}
    for i, s in enumerate(sessions):
        plan[id(s)] = "ABC"[i % 3]; expected["ABC"[i % 3]] += 1
    barrier = threading.Barrier(a.clients)
    dup_codes = []

    def vote_phase(s):
        barrier.wait()  # alle gleichzeitig
        opt = plan[id(s)]
        st, _, dt = s.req("POST", "/api/vote", {"option": opt, "request_id": uuid.uuid4().hex}); rec("vote", st, dt)
        # Doppelstimme mit anderer Request-ID und anderer Option
        other = "ABC"[("ABC".index(opt) + 1) % 3]
        st2, _, dt2 = s.req("POST", "/api/vote", {"option": other, "request_id": uuid.uuid4().hex}); rec("vote", st2, dt2)
        with lock: dup_codes.append(st2)
        st3, _, dt3 = s.req("GET", "/api/state"); rec("state", st3, dt3)

    print("Phase 2: %d parallele Stimmen + je eine Doppelstimme" % a.clients)
    t0 = time.perf_counter(); run(vote_phase); dur = time.perf_counter() - t0
    run(poll_phase)

    st, raw, _ = admin.req("GET", "/admin/api/state")
    live = json.loads(raw)["data"]["live"]
    admin.req("POST", "/admin/api/reset_round", {"confirm": True})

    errors_http = sum(n for (k, s), n in codes.items() if s in (0, 500, 503) or s >= 500)
    ok_votes = codes.get(("vote", 200), 0)
    print("\n=== Ergebnis ===")
    print("Dauer Stimmphase: %.2f s (%.1f Stimmen/s)" % (dur, a.clients / dur))
    for kind in ("state", "vote"):
        v = lat[kind]
        print("%-5s n=%d  median=%.0f ms  p95=%.0f ms  max=%.0f ms" % (
            kind, len(v), statistics.median(v) * 1000, pct(v, .95) * 1000, max(v) * 1000))
    print("HTTP-Codes:", {"%s %s" % k: n for k, n in sorted(codes.items())})
    checks = [
        ("Gesamtzahl Stimmen == Clients (%d)" % a.clients, live["total"] == a.clients),
        ("Verteilung stimmt", live["counts"] == expected),
        ("alle Doppelstimmen abgewiesen (409)", dup_codes.count(409) == a.clients),
        ("keine 5xx/SQLite-Lock-Fehler/Timeouts", errors_http == 0),
        ("Polling ohne Fehler", all(s == 200 for (k, s) in codes if k == "state")),
    ]
    for name, good in checks:
        print(("PASS " if good else "FAIL ") + name)
    sys.exit(0 if all(g for _, g in checks) else 1)


if __name__ == "__main__":
    main()
