# -*- coding: utf-8 -*-
# © 2015-2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase
from openerp.exceptions import ValidationError


class TestBaseBankAccountNumberUnique(TransactionCase):

    def test_base_bank_account_number_unique(self):
        """Add a bank account, then try to add another one with the
        same number."""
        bank_account_model = self.env['res.partner.bank']
        bank_account_model.create({
            'acc_number': 'BE1234567890',
            'state': 'bank',
        })
        with self.assertRaises(ValidationError):
            bank_account_model.create({
                'acc_number': 'BE 1234 567 890',
                'state': 'bank',
            })

    def test_base_bank_account_number_unique_write(self):
        """Add a bank account, then try to add another one with the
        same number."""
        bank_account_model = self.env['res.partner.bank']
        bank_account_model.create({
            'acc_number': 'BE1234567890',
            'state': 'bank',
        })
        acc = bank_account_model.create({
            'acc_number': 'CH1234567890',
            'state': 'bank',
        })
        with self.assertRaises(ValidationError):
            acc.acc_number = 'BE1234567890'

    def test_base_bank_account_number_other_company(self):
        """Add a bank account, then try to add another one with the
        same number, but belongig to another company."""
        bank_account_model = self.env['res.partner.bank']
        company_model = self.env['res.company']
        company = company_model.create({
            'name': 'Schmidt AG',
        })
        bank_account_model.create({
            'acc_number': 'BE1234567890',
            'state': 'bank',
        })
        bank_account_model.create({
            'acc_number': 'CH1234567890',
            'state': 'bank',
            'company_id': company.id,
        })

    def test_bank_account_copy(self):
        """Copied bank account data should not contain account."""
        bank_account_model = self.env['res.partner.bank']
        original_account = bank_account_model.create({
            'acc_number': 'BE1234567890',
            'state': 'bank',
        })
        copied_data = original_account.copy_data(default=None)
        # Calling copy_data from new api returns array!
        self.assertEqual(copied_data[0]['acc_number'], '')
