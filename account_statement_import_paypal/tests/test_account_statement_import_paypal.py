# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from os import path

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common


class TestAccountBankStatementImportPayPal(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.paypal_statement_map_en = self.env.ref(
            "account_statement_import_paypal.paypal_statement_map_en"
        )
        self.paypal_statement_map_es = self.env.ref(
            "account_statement_import_paypal.paypal_statement_map_es"
        )
        self.paypal_activity_map_en = self.env.ref(
            "account_statement_import_paypal.paypal_activity_map_en"
        )
        self.AccountJournal = self.env["account.journal"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountStatementImport = self.env["account.statement.import"]
        self.AccountStatementImportPayPalMapping = self.env[
            "account.statement.import.paypal.mapping"
        ]
        self.AccountStatementImportPayPalMappingWizard = self.env[
            "account.statement.import.paypal.mapping.wizard"
        ]

    def _data_file(self, filename):
        with open(path.join(path.dirname(__file__), filename)) as file:
            return b64encode(file.read().encode("utf-8"))

    def test_import_statement_en_usd(self):
        journal = self.AccountJournal.create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PP",
                "currency_id": self.currency_usd.id,
            }
        )
        wizard = self.AccountStatementImport.with_context(
            {"journal_id": journal.id}
        ).create(
            {
                "statement_filename": "fixtures/statement_en.csv",
                "statement_file": self._data_file("fixtures/statement_en.csv"),
                "paypal_mapping_id": self.paypal_statement_map_en.id,
            }
        )
        wizard.with_context(
            {
                "journal_id": journal.id,
                "account_statement_import_paypal_test": True,
            }
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 18)

    def test_import_statement_en_eur(self):
        journal = self.AccountJournal.create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PP",
                "currency_id": self.currency_eur.id,
            }
        )
        wizard = self.AccountStatementImport.with_context(
            {"journal_id": journal.id}
        ).create(
            {
                "statement_filename": "fixtures/statement_en.csv",
                "statement_file": self._data_file("fixtures/statement_en.csv"),
                "paypal_mapping_id": self.paypal_statement_map_en.id,
            }
        )
        wizard.with_context(
            {
                "journal_id": journal.id,
                "account_statement_import_paypal_test": True,
            }
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 8)

    def test_import_statement_es(self):
        journal = self.AccountJournal.create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PP",
                "currency_id": self.currency_eur.id,
            }
        )
        wizard = self.AccountStatementImport.with_context(
            {"journal_id": journal.id}
        ).create(
            {
                "statement_filename": "fixtures/statement_es.csv",
                "statement_file": self._data_file("fixtures/statement_es.csv"),
                "paypal_mapping_id": self.paypal_statement_map_es.id,
            }
        )
        wizard.with_context(
            {
                "journal_id": journal.id,
                "account_statement_import_paypal_test": True,
            }
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 8)

    def test_import_activity_en(self):
        journal = self.AccountJournal.create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PP",
                "currency_id": self.currency_usd.id,
            }
        )
        wizard = self.AccountStatementImport.with_context(
            {"journal_id": journal.id}
        ).create(
            {
                "statement_filename": "fixtures/activity_en.csv",
                "statement_file": self._data_file("fixtures/activity_en.csv"),
                "paypal_mapping_id": self.paypal_activity_map_en.id,
            }
        )
        wizard.with_context(
            {
                "journal_id": journal.id,
                "account_statement_import_paypal_test": True,
            }
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 71)

    def test_import_empty_activity(self):
        journal = self.AccountJournal.create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PP",
                "currency_id": self.currency_usd.id,
            }
        )
        wizard = self.AccountStatementImport.with_context(
            {"journal_id": journal.id}
        ).create(
            {
                "statement_filename": "fixtures/empty_activity.csv",
                "statement_file": self._data_file("fixtures/empty_activity.csv"),
                "paypal_mapping_id": self.paypal_activity_map_en.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                {
                    "journal_id": journal.id,
                    "account_statement_import_paypal_test": True,
                }
            ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 0)

    def test_import_activity_mapping_en(self):
        with common.Form(self.AccountStatementImportPayPalMappingWizard) as form:
            form.filename = "fixtures/activity_en.csv"
            form.data_file = self._data_file("fixtures/activity_en.csv")
            self.assertEqual(
                len(
                    self.AccountStatementImportPayPalMappingWizard.with_context(
                        header=form.header,
                    ).statement_columns()
                ),
                22,
            )
            wizard = form.save()
        wizard.import_mapping()

    def test_import_statement_mapping_en(self):
        with common.Form(self.AccountStatementImportPayPalMappingWizard) as form:
            form.filename = "fixtures/statement_en.csv"
            form.data_file = self._data_file("fixtures/statement_en.csv")
            self.assertEqual(
                len(
                    self.AccountStatementImportPayPalMappingWizard.with_context(
                        header=form.header,
                    ).statement_columns()
                ),
                18,
            )
            wizard = form.save()
        wizard.import_mapping()
