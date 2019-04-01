# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tools.misc import file_open
from odoo.tests.common import TransactionCase


class TestAccountBankStatementImportMt940NlMollie(TransactionCase):
    def test_account_bank_statement_import_mt940_nl_mollie(self):
        currency_code, account_number, statement_data = self.env[
            'account.bank.statement.import'
        ]._parse_file(
            file_open(
                'account_bank_statement_import_mt940_nl_mollie/examples/'
                'Voorbeeld MT-940.mt940',
            ).read(),
        )
        self.assertEqual(currency_code, 'EUR')
        self.assertEqual(account_number, 'NL30ABNA000000000000')
        self.assertEqual(len(statement_data), 1)
        statement = statement_data[0]
        self.assertEqual(len(statement['transactions']), 21)
        self.assertEqual(statement['balance_end_real'], -1350.26)
        self.assertAlmostEqual(
            statement['balance_end_real'],
            sum(t['amount'] for t in statement['transactions']),
        )
