# -*- coding: utf-8 -*-
"""Extend res.partner.bank."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import re
from openerp.osv import orm


class ResPartnerBank(orm.Model):
    """Extend res.partner.bank."""
    _inherit = 'res.partner.bank'

    def get_unique_account_identifier(self, cr, account):
        """
        Get an identifier for a local bank account, based on the last
        characters of the account number with minimum length 3.
        The identifier should be unique amongst the company accounts

        Presumably, the bank account is one of the company accounts
        itself but importing bank statements for non-company accounts
        is not prevented anywhere else in the system so the 'account'
        param being a company account is not enforced here either.
        """
        def normalize(account_no):
            """Do away with whitespace in bank account number."""
            return re.sub(r'\s', '', account_no)

        account = normalize(account)
        cr.execute(
            """SELECT acc_number FROM res_partner_bank
               WHERE company_id IS NOT NULL""")
        accounts = [normalize(row[0]) for row in cr.fetchall()]
        tail_length = 3
        while tail_length <= len(account):
            tail = account[-tail_length:]
            if len([acc for acc in accounts if acc.endswith(tail)]) < 2:
                return tail
            tail_length += 1
        return account

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
