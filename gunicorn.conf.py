"""Gunicorn fuer SQLite: genau ein Worker, acht Threads. Entry Point: wsgi:app"""
import os

bind = "%s:%s" % (os.environ.get("HOST", "0.0.0.0"), os.environ.get("PORT", "5000"))
workers = 1
threads = 8
timeout = 30
graceful_timeout = 30
accesslog = None
errorlog = "-"


def post_worker_init(worker):
    from wsgi import app
    from votingapp.services.audit import log_startup
    with app.app_context():
        log_startup()
