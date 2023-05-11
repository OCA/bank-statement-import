# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import werkzeug
from werkzeug.urls import url_encode

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class NordigenController(http.Controller):
    @http.route("/nordigen/response", type="http", auth="public", csrf=False)
    def nordigen_response(self, **post):
        _logger.debug(post)
        statement_provider = request.env["online.bank.statement.provider"].sudo()
        current_provider = statement_provider.search(
            [("nordigen_last_requisition_ref", "=", post.get("ref", False))]
        )
        action_id = request.env.ref(
            "account_statement_import_online.online_bank_statement_provider_action"
        ).id
        params = {
            "action": action_id,
            "view_type": "list",
        }
        url = "/web#" + url_encode(params)
        if current_provider:
            current_provider.update_nordigen_request()
            url = current_provider._get_nordigen_url_action()
        return werkzeug.utils.redirect(url, 303)
