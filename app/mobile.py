import re
from flask import request, g

_MOBILE_RE = re.compile(
    r"android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini",
    re.IGNORECASE,
)


def detect_mobile() -> bool:
    ua = request.headers.get("user-agent", "")
    is_mobile_ua = bool(_MOBILE_RE.search(ua))
    override = request.cookies.get("mobile_override")
    if override == "mobile":
        return True
    if override == "desktop":
        return False
    return is_mobile_ua


def init_mobile(app):
    @app.before_request
    def set_mobile():
        g.is_mobile = detect_mobile()
