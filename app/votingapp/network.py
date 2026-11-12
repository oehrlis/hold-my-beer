import socket

from flask import current_app, request


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # sendet nichts, ermittelt nur die Route
            return s.getsockname()[0]
    except OSError:
        return None


def public_base_url():
    """PUBLIC_BASE_URL, sonst automatisch erkannte lokale Adresse (z.B. WSL2-IP)."""
    cfg = current_app.config["PUBLIC_BASE_URL"]
    if cfg:
        return cfg
    ip = local_ip()
    if ip:
        return "http://%s:%s" % (ip, current_app.config["PORT"])
    return request.host_url.rstrip("/")
