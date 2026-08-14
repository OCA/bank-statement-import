# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2025 Simone Rubino
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from .common import Common


class TestAccountStatementImportSheetFile(Common):
    def test_import_html_file(self):
        """Import an XLS[X] file that is actually an HTML file."""
        wizard = self._get_import_wizard("data/sample_statement_html.xlsx")
        wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertRecordValues(
            statement.line_ids,
            [
                {
                    "date": date(2025, month=1, day=15),
                    "payment_ref": "Line description",
                    "partner_name": "Azure Interior",
                    "amount": -200.20,
                },
            ],
        )
