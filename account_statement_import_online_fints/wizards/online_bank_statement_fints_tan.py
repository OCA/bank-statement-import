# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64decode
from hashlib import sha256

from fints.client import NeedRetryResponse, NeedTANResponse

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import consteq, hmac


class OnlineBankStatementFintsTan(models.TransientModel):
    _name = "online.bank.statement.fints.tan"
    _description = "Confirm the bank access of a FinTS provider"

    provider_id = fields.Many2one(
        comodel_name="online.bank.statement.provider",
        required=True,
        ondelete="cascade",
    )
    # State of the paused FinTS dialog and of the TAN request
    dialog_data = fields.Binary(attachment=False, required=True)
    tan_data = fields.Binary(attachment=False, required=True)
    # The paused dialog is restored with pickle: only data signed by the
    # server may be restored, a user can write the wizard
    signature = fields.Char(readonly=True)
    decoupled = fields.Boolean(readonly=True)
    challenge = fields.Html(readonly=True, sanitize=True)
    challenge_image = fields.Image(readonly=True, attachment=False)
    challenge_hhduc = fields.Char(string="Flicker Code", readonly=True)
    tan = fields.Char(string="TAN")
    pending = fields.Boolean(
        readonly=True,
        help="The confirmation in the banking app is still pending.",
    )

    @api.model
    def _get_signature(self, provider, dialog_data, tan_data):
        """Return the signature of the paused dialog and of the TAN request
        of a provider, given as bytes"""
        message = ":".join(
            [
                str(provider.id),
                sha256(dialog_data).hexdigest(),
                sha256(tan_data).hexdigest(),
            ]
        )
        return hmac(
            self.env(su=True), "account_statement_import_online_fints.tan", message
        )

    def action_confirm(self):
        self.ensure_one()
        provider = self.provider_id
        dialog_data = b64decode(self.dialog_data)
        tan_data = b64decode(self.tan_data)
        if not consteq(
            self.signature or "", self._get_signature(provider, dialog_data, tan_data)
        ):
            raise UserError(
                self.env._(
                    "The confirmation data of provider %s is invalid, click on "
                    "'Connect' again.",
                    provider.name,
                )
            )
        client = provider._fints_get_client()
        challenge = NeedRetryResponse.from_data(tan_data)
        challenge.decoupled = self.decoupled
        with client.resume_dialog(dialog_data):
            response = client.send_tan(challenge, self.tan or "")
            if not isinstance(response, NeedTANResponse):
                response = provider._fints_continue_connect(client, response)
            if response:
                dialog_data = client.pause_dialog()
        if response:
            action = provider._fints_request_tan(client, response, dialog_data)
            # Still the same decoupled confirmation, which is not done yet
            if self.decoupled and response.decoupled:
                self.env[action["res_model"]].browse(action["res_id"]).pending = True
            return action
        return provider._fints_connected(client)
