# -*- coding: utf-8 -*-
# ©  2016 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImport(TestStatementFile):
    """Run test to import MT940 ING import."""

    def test_statement_import(self):
        """Test correct creation of single statement."""
        self._test_statement_import(
            'account_bank_statement_import_mt940_ro_brd', 'test-brd.940',
            '00138/1',
            start_balance=3885.24, end_balance=3671.88
        )
