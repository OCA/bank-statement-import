# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV <http://therp.nl>.
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
from openerp import _, SUPERUSER_ID, exceptions


def post_init_hook(cr, pool):
    '''check if your constraint was actually inserted, raise otherwise'''
    if not pool['ir.model.constraint'].search(cr, SUPERUSER_ID, [
        ('name', '=', 'res_partner_bank_unique_number'),
        ('model.model', '=', 'res.partner.bank'),
    ]):
        max_account_numbers = 10
        cr.execute(
            """
            with
            res_partner_bank_sanitized as
            (select id, acc_number, regexp_replace(acc_number, '\\W+', '', 'g')
             acc_number_sanitized from res_partner_bank),
            res_partner_bank_sanitized_grouped as
            (select array_agg(id) ids, acc_number_sanitized, count(*) amount
             from res_partner_bank_sanitized group by acc_number_sanitized)
            select acc_number_sanitized from res_partner_bank_sanitized_grouped
            where amount > 1 limit %s;
            """,
            (max_account_numbers,))
        duplicates = [acc_number for acc_number, in cr.fetchall()]
        message = _(
            "Module installation can't proceed as you have duplicate "
            "account numbers in your system already. Please clean that up "
            "and try again.\n"
            "The following shows the first %d duplicate account numbers\n"
            "%s\n"
            "(if you see less than %d, those are the only duplicates)") % (
                max_account_numbers, '\n'.join(duplicates),
                max_account_numbers,
        )
        raise exceptions.Warning(message)
