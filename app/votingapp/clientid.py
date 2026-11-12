"""Anonyme Client-ID: zufaellig, in signiertem Cookie; in der DB liegt nur ein HMAC-Hash."""
import hashlib
import hmac
import secrets

from flask import current_app, g, request
from itsdangerous import BadSignature, URLSafeSerializer

COOKIE = "olv_cid"


def _serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="client-id")


def get_client_id(create=False):
    raw = request.cookies.get(COOKIE)
    if raw:
        try:
            return _serializer().loads(raw)
        except BadSignature:
            pass
    if create:
        if "new_cid" not in g:
            g.new_cid = secrets.token_urlsafe(24)
        return g.new_cid
    return None


def hash_client_id(cid):
    if not cid:
        return None
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, cid.encode(), hashlib.sha256).hexdigest()


def rate_key():
    cid = get_client_id()
    return "c:" + cid if cid else "ip:" + (request.remote_addr or "?")


def attach_cookie(response):
    cid = g.get("new_cid")
    if cid:
        response.set_cookie(COOKIE, _serializer().dumps(cid), max_age=60 * 60 * 24 * 365, httponly=True,
                            samesite="Lax", secure=current_app.config["SESSION_COOKIE_SECURE"])
    return response
