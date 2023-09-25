# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=missing-docstring,invalid-name,protected-access
import logging
from html import escape

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource

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
        result = None  # Need because of super() call.
        adyen_providers = self.filtered(lambda r: r.service in ("adyen", "dummy_adyen"))
        other_providers = self.filtered(
            lambda r: r.service not in ("adyen", "dummy_adyen")
        )
        if other_providers:
            result = super(OnlineBankStatementProvider, other_providers)._pull(
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
        return result

    def _import_adyen_file(self):
        """Import Adyen file using functionality from manual Adyen import module."""
        self.ensure_one()
        if self.service == "dummy_adyen":
            data_file, file_name = self._adyen_dummy_get_settlement_details_file()
        else:
            data_file, file_name = self._adyen_get_settlement_details_file()
        wizard_model = self.env["account.statement.import"]
        wizard = wizard_model.create(
            {
                "statement_filename": file_name,  # Only need the name in the wizard
            }
        )
        currency_code, account_number, stmts_vals = wizard._parse_adyen_file(data_file)
        success = wizard._check_parsed_data(stmts_vals)
        if not success:
            _logger.debug("Parser did not return valid statement data", stmts_vals)
        else:
            # Result is used in file import to collect result of several statements.
            result = {
                "statement_ids": [],
                "notifications": [],  # list of text messages
            }
            stmts_vals = wizard._complete_stmts_vals(
                stmts_vals, self.journal_id, account_number
            )
            wizard._create_bank_statements(stmts_vals, result)

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
        response = requests.get(URL, auth=(self.username, self.password), timeout=30)
        if response.status_code != 200:
            raise UserError(
                _("%(status_code)s \n\n %(text)s")
                % {"status_code": response.status_code, "text": response.text}
            )
        _logger.debug("Headers returned by Adyen %s", response.headers)
        byte_count = len(response.content)
        _logger.debug(
            "Retrieved %d bytes from Adyen, starting with %s",
            byte_count,
            response.content[:64],
        )
        return response.content, filename

    def _adyen_dummy_get_settlement_details_file(self):
        """Get file from disk, instead of from url."""
        filename = self.download_file_name
        testfile = get_module_resource(
            "account_statement_import_adyen", "test_files", filename
        )
        with open(testfile, "rb") as datafile:
            data_file = datafile.read()
        return data_file, filename

    def _schedule_next_run(self):
        """Set next run date and autoincrement batch number."""
        result = super()._schedule_next_run()
        self.next_batch_number += 1
        return result
