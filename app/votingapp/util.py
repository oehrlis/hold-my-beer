from datetime import datetime, timezone

from flask import jsonify


def utcnow():
    """Aktuelle UTC-Zeit als naive datetime (so wird sie in SQLite gespeichert)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if dt else None


class ApiError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def ok(data=None, message=None, status=200):
    body = {"ok": True, "data": data if data is not None else {}}
    if message:
        body["message"] = message
    return jsonify(body), status


def fail(code, message, status=400):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status
