# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format
    (account.bank.statement.import)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.statement_import_model = cls.env["account.statement.import"]
        cls.statement_line_model = cls.env["account.bank.statement.line"]
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test bank journal",
                "code": "TEST",
                "type": "bank",
                "currency_id": cls.env.company.currency_id.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                # Different case for trying insensitive case search
                "name": "EPIC Technologies",
            }
        )

    def test_qif_file_import(self):
        qif_file_path = get_module_resource(
            "account_statement_import_qif",
            "tests",
            "test_qif.qif",
        )
        qif_file = base64.b64encode(open(qif_file_path, "rb").read())
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create({"statement_file": qif_file, "statement_filename": "test_qif.qif"})
        wizard.import_file_button()
        statement = self.statement_line_model.search(
            [("payment_ref", "=", "YOUR LOCAL SUPERMARKET")],
            limit=1,
        ).statement_id
        self.assertAlmostEqual(statement.balance_end_real, -1896.09, 2)
        line = self.statement_line_model.search(
            [("payment_ref", "=", "Epic Technologies")],
            limit=1,
        )
        self.assertEqual(line.partner_id, self.partner)
