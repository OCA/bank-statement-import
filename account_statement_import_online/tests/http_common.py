# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from contextlib import contextmanager
from unittest.mock import Mock, patch

import requests

from odoo.tests.common import _super_send


@contextmanager
def mock_http_responses(*responses):
    """Exercise Requests' redirect policy through an entirely offline adapter."""
    with requests.Session() as session:
        session.trust_env = False
        # Keep Odoo's global network blocker; only this offline session uses send.
        session.send = _super_send.__get__(session, type(session))
        adapter = Mock(spec=requests.adapters.BaseAdapter)
        adapter.send.side_effect = responses
        session.get_adapter = Mock(return_value=adapter)
        with patch("requests.sessions.Session", return_value=session):
            yield adapter.send
