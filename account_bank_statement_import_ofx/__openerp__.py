# -*- encoding: utf-8 -*-
# noqa: This is a backport from Odoo. OCA has no control over style here.
# flake8: noqa
{
    'name': 'Import OFX Bank Statement',
    'version': '1.0',
    'author': 'OpenERP SA',
    'website': 'https://github.com/OCA/bank-statement-import',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import',
        'bank_statement_parse',  # Added in backport.
    ],
    'demo': [],
    'description' : """
Module to import OFX bank statements.
======================================

This module allows you to import the machine readable OFX Files in Odoo: they are parsed and stored in human readable format in 
Accounting \ Bank and Cash \ Bank Statements.

Bank Statements may be generated containing a subset of the OFX information (only those transaction lines that are required for the 
creation of the Financial Accounting records). 
    
Backported from Odoo 9.0

When testing with the provided test file, make sure the demo data from the
base account_bank_statement_import module has been imported, or manually
create periods for the year 2013.
    """,
    'data' : [],
    'demo': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
