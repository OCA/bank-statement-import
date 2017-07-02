# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_import is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.tests.common import TransactionCase
from openerp.exceptions import Warning as UserError


class TestAccountBankStatementImport(TransactionCase):
    """Tests for import bank statement file import
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestAccountBankStatementImport, self).setUp()
        self.statement_import_model = self.env[
            'account.bank.statement.import']
        self.account_journal_model = self.env['account.journal']
        self.res_users_model = self.env['res.users']

        self.journal_id = self.ref('account.bank_journal')
        self.base_user_root_id = self.ref('base.user_root')
        self.base_user_root = self.res_users_model.browse(
            self.base_user_root_id)

        # create a new user that belongs to the same company as
        # user_root
        self.other_partner_id = self.env['res.partner'].create(
            {"name": "My other partner",
             "is_company": False,
             "email": "test@tes.ttest",
             })
        self.company_id = self.base_user_root.company_id.id
        self.other_user_id_a = self.res_users_model.create(
            {"partner_id": self.other_partner_id.id,
             "company_id": self.company_id,
             "company_ids": [(4, self.company_id)],
             "login": "my_login a",
             "name": "my user",
             "groups_id": [(4, self.ref('account.group_account_manager'))]
             })

    def test_import_preconditions(self):
        """Checks that the import raises an exception if:
         * no bank account found for the account_number
         * if the bank account exists, but is not for a company

         The message 'Can not determine journal' is now very hard to trigger
         because the system sets a journal on a bank account, as soon as it
         is linked to a company.
        """
        def assert_raise_no_account(stmt_vals):
            import_model = self.env['account.bank.statement.import']
            with self.assertRaises(UserError) as e:
                import_model._import_statement(stmt_vals.copy())
            self.assertEqual(
                e.exception.message,
                'Can not find the account number 123456789.'
            )

        ACCOUNT_NUMBER = '123456789'
        stmt_vals = {
            'currency_code': 'EUR',
            'account_number': ACCOUNT_NUMBER,
        }
        # Check error before any bank created
        assert_raise_no_account(stmt_vals)
        # Now create a non company account. Error should still be raised
        import_model = self.env['account.bank.statement.import']
        import_model._create_bank_account(ACCOUNT_NUMBER)
        assert_raise_no_account(stmt_vals)

    def test_find_company_bank_account_id(self):
        """Checks wether code can find the right bank account.
         * With duplicates, take the one for the company
         * With no account number specified, use journal to find account
        """
        import_model = self.env['account.bank.statement.import']
        ACCOUNT_NUMBER = '123456789'
        self.statement_import_model._create_bank_account(
            ACCOUNT_NUMBER
        )
        company_bank = self.statement_import_model._create_bank_account(
            ACCOUNT_NUMBER, company_id=self.env.user.company_id.id
        )
        # Create another company bank account
        self.statement_import_model._create_bank_account(
            '987654321', company_id=self.env.user.company_id.id
        )
        # find bank account with account number
        found_id = import_model._find_company_bank_account_id(ACCOUNT_NUMBER)
        self.assertEqual(found_id, company_bank.id)
        # find bank account with journal
        found_id = import_model.with_context(
            journal_id=company_bank.journal_id.id,
        )._find_company_bank_account_id('')
        self.assertEqual(found_id, company_bank.id)

    def test_create_bank_account(self):
        """Checks that the bank_account created by the import belongs to the
        partner linked to the company of the provided journal
        """
        journal = self.account_journal_model.browse(self.journal_id)
        expected_id = journal.company_id.partner_id.id
        st_import = self.statement_import_model.sudo(self.other_user_id_a.id)
        bank = st_import._create_bank_account(
            '001251882303', company_id=self.company_id)
        self.assertEqual(bank.partner_id.id, expected_id)
