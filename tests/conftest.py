import re
from datetime import timedelta

import pytest

from votingapp import create_app
from votingapp.extensions import db
from votingapp.models import SessionState
from votingapp.services.seed import seed_data
from votingapp.util import utcnow

PASSWORD = "test-admin-pw"


def make_app(tmp_path, **extra):
    cfg = {"APP_ENV": "testing", "SQLALCHEMY_DATABASE_URI": "sqlite:///%s" % (tmp_path / "test.db"),
           "SECRET_KEY": "test-secret", "ADMIN_PASSWORD": PASSWORD}
    cfg.update(extra)
    app = create_app(cfg)
    with app.app_context():
        db.create_all()
        seed_data()
    return app


class Client:
    """Test-Client mit CSRF-Handling und JSON-Helfern."""

    def __init__(self, app):
        self.app = app
        self.http = app.test_client()
        self.token = None

    def csrf(self):
        if self.token is None:
            html = self.http.get("/").get_data(as_text=True)
            self.token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
        return self.token

    def get(self, url):
        return self.http.get(url)

    def post(self, url, body=None, csrf=True):
        headers = {"X-CSRFToken": self.csrf()} if csrf else {}
        return self.http.post(url, json=body or {}, headers=headers)

    def state(self):
        return self.get("/api/state").get_json()["data"]

    def cid(self):
        self.state()
        return self.http.get_cookie("olv_cid").value

    def login(self, password=PASSWORD):
        r = self.http.post("/admin/login", data={"password": password, "csrf_token": self.csrf()})
        self.token = None  # Session wurde erneuert -> wie im Browser neue Seite/neuen Token laden
        return r

    def admin(self, action, body=None):
        return self.post("/admin/api/" + action, body)

    def astate(self):
        return self.get("/admin/api/state").get_json()["data"]


@pytest.fixture
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture
def client(app):
    return Client(app)


@pytest.fixture
def admin(app):
    c = Client(app)
    assert c.login().status_code == 302
    return c


def new_clients(app, n):
    return [Client(app) for _ in range(n)]


def expire_voting(app):
    with app.app_context():
        ss = db.session.get(SessionState, 1)
        ss.voting_ends_at = utcnow() - timedelta(seconds=1)
        db.session.commit()


def open_round(admin, duration=60):
    assert admin.admin("open_voting", {"duration": duration}).status_code == 200


def play_to_result(admin, votes):
    """votes: Liste von Optionen, jeweils von einem frischen Client abgegeben."""
    open_round(admin)
    for opt in votes:
        c = Client(admin.app)
        assert c.post("/api/vote", {"option": opt, "request_id": "r" * 8 + str(id(c))}).status_code == 200
    assert admin.admin("close_voting").status_code == 200
    assert admin.admin("publish_result").status_code == 200
