# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit


def validate_api_url(url, allowed_hosts):
    """Validate and canonicalise a provider URL before attaching credentials."""
    if any(ord(char) <= 32 or ord(char) == 127 for char in url):
        raise ValueError("Control characters or spaces in API URL")
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in allowed_hosts
        or parts.port not in (None, 443)
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise ValueError("Untrusted API destination")
    return urlunsplit(("https", parts.hostname, parts.path, parts.query, ""))


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        fp.close()
        raise HTTPError(req.full_url, code, msg, headers, None)

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302
