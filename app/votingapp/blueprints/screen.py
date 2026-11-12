import io

import qrcode
import qrcode.image.svg
from flask import Blueprint, Response, current_app, render_template

from ..network import public_base_url

bp = Blueprint("screen", __name__)


def share_url():
    """Ziel des Teilen-QR-Codes: SHARE_URL, sonst die Teilnahme-URL."""
    return (current_app.config.get("SHARE_URL") or public_base_url()) + "/"


@bp.app_context_processor
def _share_ctx():
    return {"share_url": share_url}  # Funktion, wird nur in _share_qr.html aufgerufen


@bp.get("/screen")
def screen():
    return render_template("screen.html", public_url=public_base_url())


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
