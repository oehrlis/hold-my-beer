import io

import qrcode
import qrcode.image.svg
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, render_template, send_file

from ..network import public_base_url

bp = Blueprint("screen", __name__)


def share_url():
    """Ziel des Teilen-QR-Codes: SHARE_URL, sonst die Teilnahme-URL."""
    return (current_app.config.get("SHARE_URL") or public_base_url()) + "/"


@bp.app_context_processor
def _share_ctx():
    return {"share_url": share_url}  # Funktion, wird nur in _share_qr.html aufgerufen


def _burp_path():
    p = current_app.config.get("BURP_FILE")
    return Path(p) if p and Path(p).is_file() else None


@bp.get("/screen")
def screen():
    return render_template("screen.html", public_url=public_base_url(), burp=_burp_path() is not None)


@bp.get("/screen/burp")
def burp():
    """Rülps-Ton fuer /screen; 404, solange BURP_FILE nicht gesetzt ist oder fehlt."""
    p = _burp_path()
    if p is None:
        abort(404)
    return send_file(p, max_age=3600)


@bp.get("/qr.svg")
def qr():
    return _qr_response(public_base_url() + "/")


@bp.get("/share-qr.svg")
def share_qr():
    return _qr_response(share_url())


def _qr_response(url):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control": "no-store"})
