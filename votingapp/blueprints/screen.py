import io

import qrcode
import qrcode.image.svg
from flask import Blueprint, Response, render_template

from ..network import public_base_url

bp = Blueprint("screen", __name__)
SHARE_URL = "http://<host-ip>:8080/"


@bp.get("/screen")
def screen():
    return render_template("screen.html", public_url=public_base_url())


@bp.get("/qr.svg")
def qr():
    return _qr_response(public_base_url() + "/")


@bp.get("/share-qr.svg")
def share_qr():
    return _qr_response(SHARE_URL)


def _qr_response(url):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control": "no-cache"})
