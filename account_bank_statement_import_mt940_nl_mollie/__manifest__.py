# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "MT940 Bank Statements Import (Mollie)",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Banking Addons",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": [
        'account_bank_statement_import_mt940_base',
    ],
    "data": [
        "views/account_bank_statement_import.xml",
    ],
}
