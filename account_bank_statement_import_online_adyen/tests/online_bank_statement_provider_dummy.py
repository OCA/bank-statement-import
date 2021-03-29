# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64

from odoo import models
from odoo.modules.module import get_module_resource


class OnlineBankStatementProviderDummy(models.Model):
    _inherit = "online.bank.statement.provider"

    def _adyen_get_settlement_details_file(self):
        """Get file from disk, instead of from url."""
        if self.service != "dummy_adyen":
            # Not a dummy, get the regular adyen method.
            return super()._adyen_get_settlement_details_file()
        filename = self.download_file_name
        testfile = get_module_resource(
            "account_bank_statement_import_adyen", "test_files", filename
        )
        with open(testfile, "rb") as datafile:
            data_file = datafile.read()
            data_file = base64.b64encode(data_file)
        return data_file, filename
