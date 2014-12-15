# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#              (C) 2011-2104 Therp BV (<http://therp.nl>).
#              (C) 2011 Smile (<http://smile.fr>).
#
#    All other contributions are (C) by their respective contributors
#
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Bank Statement Import Parse',
    'version': '0.5',
    'license': 'AGPL-3',
    'author': 'Banking addons community',
    'website': 'https://github.com/OCA/banking',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import',
        ],
    'data': [
        # 'security/ir.model.access.csv',
        # 'wizard/bank_import_view.xml',
        'view/account_bank_statement_import.xml',
        'view/bank_statement_import_settings.xml',
        'view/menu.xml',
    ],
    'js': [
    ],
    'description': '''
    Base module to write parsers for bank statement import files.

    The module account_bank_statement_import, backported from odoo 9.0, is
    exentended, so parsers developed might hope to be compatible with future
    development of Odoo.

    This module extends the base functionality by:
    - more extensive logging
    - storing much more information on each bank transaction in the bank
      statement line
    - making all imports visible for the user, complete with log and data about
      user and date of import.

    This module also should make it easy to migrate bank statement import
    moduels written for earlies versions of Odoo/OpenERP.
    
    Changes to default Odoo:

    * Puts focus on the real life messaging with banks:
      + Bank statement lines upgraded to independent bank transactions.
      + Banking statements have no special accountancy meaning, they're just
        message envelopes for a number of bank transactions.
      + Bank statements can be either encoded by hand to reflect the document
        version of Bank Statements, or created as an optional side effect of
        importing Bank Transactions.

    * Adds dropin extensible import facility for bank communication in:
      - Drop-in input parser development.

    * Additional features for the import/export mechanism:
      + Automatic matching and creation of bank accounts, banks and partners,
        during import of statements.
      + Automatic matching with invoices and payments.
      + Sound import mechanism, allowing multiple imports of the same
        transactions repeated over multiple files.
      + Journal configuration per bank account.
      + Business logic and format parsing strictly separated to ease the
        development of new parsers.
      + No special configuration needed for the parsers, new parsers are
        recognized and made available at server (re)start.
    ''',
    'installable': True,
    'auto_install': False,
}
