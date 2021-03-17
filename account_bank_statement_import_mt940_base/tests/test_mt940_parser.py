# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase

from openerp.addons.account_bank_statement_import.parserlib import \
    BankTransaction

from ..mt940 import str2amount, get_subfields, handle_common_subfields


RECORD86 = (
    ":86:/EREF/ZZ12T32FYCIO7YPXC//CNTP/FR7630239881239147035594069/BNP"
    "AFRPP/JOHN WHO PAID///REMI/USTD//virt AD 934637/")
CODEWORDS = [
    'RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF', 'EREF',
    'PREF', 'REMI', 'ID', 'PURP', 'ULTB', 'ULTD',
    'CREF', 'IREF', 'CNTP', 'ULTC', 'EXCH', 'CHGS']


class TestMT940Parser(TransactionCase):
    """Test common methods in mt940 parser."""

    def test_str2amount(self):
        """Test conversion of string to amount."""
        amount = str2amount('C', '16,16')
        self.assertEqual(amount, 16.16)
        amount = str2amount('D', '25,25')
        self.assertEqual(amount, -25.25)

    def test_get_subfields(self):
        """Test get subfields."""
        subfields = get_subfields(RECORD86, CODEWORDS)
        self.assertIn('EREF', subfields)
        self.assertEqual('ZZ12T32FYCIO7YPXC', subfields['EREF'][0])
        self.assertIn('REMI', subfields)
        self.assertEqual('virt AD 934637', subfields['REMI'][2])

    def test_handle_common_subfields(self):
        """test handle_common_subfields"""
        transaction = BankTransaction()
        subfields = get_subfields(RECORD86, CODEWORDS)
        handle_common_subfields(transaction, subfields)
        self.assertEqual('virt AD 934637', transaction.message)
        self.assertEqual('ZZ12T32FYCIO7YPXC', transaction.eref)
