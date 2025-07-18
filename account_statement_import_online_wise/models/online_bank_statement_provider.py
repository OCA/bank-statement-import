# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020-2021 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    @api.model
    def values_wise_profile(self):
        """Return values for wise profile selection in the form view."""
        api_base = self.env.context.get("api_base") or "https://api.transferwise.com"
        api_key = self.env.context.get("api_key")
        if not api_key:
            return []
        try:
            url = api_base + "/v1/profiles"
            data = self._wise_retrieve(url, api_key)
        except BaseException:
            return []
        return list(
            map(
                lambda entry: (
                    str(entry["id"]),
                    "%s %s (personal)"
                    % (
                        entry["details"]["firstName"],
                        entry["details"]["lastName"],
                    )
                    if entry["type"] == "personal"
                    else entry["details"]["name"],
                ),
                data,
            )
        )

    @api.model
    def _wise_retrieve(self, url, api_key, private_key=None):
        """Retrieve data from Wise API."""
        import json
        import urllib.request
        from base64 import b64encode
        from urllib.error import HTTPError

        try:
            request = urllib.request.Request(url)
            request.add_header("Authorization", "Bearer %s" % api_key)
            request.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(request) as response:
                content = response.read().decode(
                    response.headers.get_content_charset() or "utf-8"
                )
        except HTTPError as e:
            if e.code != 403 or e.headers.get("X-2FA-Approval-Result") != "REJECTED":
                raise e
            if not private_key:
                from odoo import _
                from odoo.exceptions import UserError

                raise UserError(_("Strong Customer Authentication is not configured"))
            one_time_token = e.headers["X-2FA-Approval"]
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            private_key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend(),
            )
            signature = private_key.sign(
                one_time_token.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

            request = urllib.request.Request(url)
            request.add_header("Authorization", "Bearer %s" % api_key)
            request.add_header("User-Agent", "Mozilla/5.0")
            request.add_header("X-2FA-Approval", one_time_token)
            request.add_header("X-Signature", b64encode(signature).decode())
            with urllib.request.urlopen(request) as response:
                content = response.read().decode(
                    response.headers.get_content_charset() or "utf-8"
                )

        content = json.loads(content)
        if "error" in content and content["error"]:
            from odoo import _
            from odoo.exceptions import UserError

            raise UserError(
                content["error_description"]
                if "error_description" in content
                else "Unknown error"
            )
        return content
