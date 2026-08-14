# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2025 Simone Rubino
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from unittest.mock import Mock

from odoo import fields, tools
from odoo.tests import common


class Common(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = "account_statement_import_sheet_file"
        cls.now = fields.Datetime.now()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.currency_usd.active = True
        # Activate EUR for unit test, by default is not active
        cls.currency_eur.active = True
        cls.sample_statement_map = cls.env.ref(
            "account_statement_import_sheet_file.sample_statement_map"
        )
        cls.AccountJournal = cls.env["account.journal"]
        cls.AccountBankStatement = cls.env["account.bank.statement"]
        cls.AccountStatementImport = cls.env["account.statement.import"]
        cls.AccountStatementImportSheetMapping = cls.env[
            "account.statement.import.sheet.mapping"
        ]
        cls.AccountStatementImportWizard = cls.env["account.statement.import"]
        cls.suspense_account = cls.env["account.account"].create(
            {
                "code": "987654",
                "name": "Suspense Account",
                "account_type": "asset_current",
            }
        )
        cls.parser = cls.env["account.statement.import.sheet.parser"]
        # Mock the mapping object to return predefined separators
        cls.mock_mapping_comma_dot = Mock()
        cls.mock_mapping_comma_dot._get_float_separators.return_value = (",", ".")
        cls.mock_mapping_dot_comma = Mock()
        cls.mock_mapping_dot_comma._get_float_separators.return_value = (".", ",")
        cls.mock_mapping_none_none = Mock()
        cls.mock_mapping_none_none._get_float_separators.return_value = ("", "")
        cls.journal = cls.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": cls.currency_usd.id,
                "suspense_account_id": cls.suspense_account.id,
            }
        )
        cls.statement_domain = [("journal_id", "=", cls.journal.id)]

    def _get_import_wizard(self, path):
        return self.AccountStatementImport.with_context(
            journal_id=self.journal.id, account_statement_import_sheet_file_test=True
        ).create(
            {
                "statement_filename": path,
                "statement_file": self._data_file(path),
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )

    def _data_file(self, filename, encoding=None):
        mode = "rt" if encoding else "rb"
        path = f"{self.module}/tests/{filename}"
        with tools.file_open(path, mode=mode) as file:
            data = file.read()
            if encoding:
                data = data.encode(encoding)
            return b64encode(data)
