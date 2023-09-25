# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=missing-docstring,invalid-name,protected-access
import base64
import logging
from html import escape

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    download_file_name = fields.Char()
    next_batch_number = fields.Integer()

    @api.model
    def _selection_service(self):
        res = super()._selection_service()
        res.append(("dummy_adyen", "Dummy Adyen"))
        return res

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [("adyen", "Adyen payment report")]

    def _pull(self, date_since, date_until):  # noqa: C901
        """Split between adyen providers and others."""
        adyen_providers = self.filtered(lambda r: r.service in ("adyen", "dummy_adyen"))
        other_providers = self.filtered(
            lambda r: r.service not in ("adyen", "dummy_adyen")
        )
        if other_providers:
            super(OnlineBankStatementProvider, other_providers)._pull(
                date_since, date_until
            )
        for provider in adyen_providers:
            is_scheduled = self.env.context.get("scheduled")
            try:
                self._import_adyen_file()
            except BaseException as e:
                if is_scheduled:
                    _logger.warning(
                        'Online Bank Statement Provider "%s" failed to'
                        " obtain statement data",
                        provider.name,
                        exc_info=True,
                    )
                    provider.message_post(
                        body=_(
                            "Failed to obtain statement data for period "
                            ": %s. See server logs for more details."
                        )
                        % (escape(str(e)) or _("N/A"),),
                        subject=_("Issue with Online Bank Statement Provider"),
                    )
                    break
                raise
            if is_scheduled:
                provider._schedule_next_run()

    def _import_adyen_file(self):
        """Import Adyen file using functionality from manual Adyen import module."""
        self.ensure_one()
        content, attachment_vals = self._get_attachment_vals()
        wizard = (
            self.env["account.bank.statement.import"]
            .with_context({"journal_id": self.journal_id.id})
            .create({"attachment_ids": [(0, 0, attachment_vals)]})
        )
        currency_code, account_number, stmts_vals = wizard._parse_adyen_file(content)
        wizard._check_parsed_data(stmts_vals, account_number)
        _currency, journal = wizard._find_additional_data(currency_code, account_number)
        stmts_vals = wizard._complete_stmts_vals(stmts_vals, journal, account_number)
        wizard._create_bank_statements(stmts_vals)

    def _get_attachment_vals(self):
        """Retrieve settlement details and convert to attachment vals."""
        content, filename = self._adyen_get_settlement_details_file()
        encoded_content = base64.encodebytes(content)
        # Make sure base64 encoded content contains multiple of 4 bytes.
        byte_count = len(encoded_content)
        byte_padding = b"=" * (byte_count % 4)
        data_file = encoded_content + byte_padding
        attachment_vals = {"name": filename, "datas": data_file}
        return content, attachment_vals

    def _adyen_get_settlement_details_file(self):
        """Retrieve daily generated settlement details file.

        The file could be retrieved with wget using:
        $ wget \
            --http-user='[YourReportUser]@Company.[YourCompanyAccount]' \
            --http-password='[YourReportUserPassword]' \
            --quiet --no-check-certificate \
            https://ca-test.adyen.com/reports/download/MerchantAccount/ +
                [YourMerchantAccount]/[ReportFileName]"
        """
        batch_number = self.next_batch_number
        filename = self.download_file_name % batch_number
        URL = "/".join(
            [self.api_base, self.journal_id.adyen_merchant_account, filename]
        )
        response = requests.get(URL, auth=(self.username, self.password))
        if response.status_code != 200:
            raise UserError(_("%s \n\n %s") % (response.status_code, response.text))
        _logger.debug(_("Headers returned by Adyen %s"), response.headers)
        byte_count = len(response.content)
        _logger.debug(
            _("Retrieved %d bytes from Adyen, starting with %s"),
            byte_count,
            response.content[:64],
        )
        return response.content, filename

    def _schedule_next_run(self):
        """Set next run date and autoincrement batch number."""
        super()._schedule_next_run()
        self.next_batch_number += 1
