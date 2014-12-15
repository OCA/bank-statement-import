# -*- coding: utf-8 -*-
# noqa: This is a backport from Odoo. OCA has no control over style here.
# flake8: noqa
{
    'name': 'Import QIF Bank Statement',
    'version': '1.0',
    'author': 'OpenERP SA',
    'description': '''
Module to import QIF bank statements.
======================================

This module allows you to import the machine readable QIF Files in Odoo: they are parsed and stored in human readable format in 
Accounting \ Bank and Cash \ Bank Statements.

Bank Statements may be generated containing a subset of the QIF information (only those transaction lines that are required for the 
creation of the Financial Accounting records). 

Backported from Odoo 9.0

When testing with the provided test file, make sure the demo data from the
base account_bank_statement_import module has been imported, or manually
create periods for the year 2013.
''',
    'images' : [],
    'depends': ['account_bank_statement_import'],
    'demo': [],
    'data': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
