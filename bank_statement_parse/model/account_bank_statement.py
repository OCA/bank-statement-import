# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2014 Therp BV (<http://therp.nl>).
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
from openerp.osv import orm, fields
from openerp.tools.translate import _


class account_bank_statement(orm.Model):
    _inherit = 'account.bank.statement'

    def _end_balance(self, cr, uid, ids, name, attr, context=None):
        """
        This method taken from account/account_bank_statement.py and
        altered to take the statement line subflow into account
        """
        res = {}

        statements = self.browse(cr, uid, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start

            # Calculate the balance based on the statement line amounts
            # ..they are in the statement currency, no conversion needed.
            for line in statement.line_ids:
                res[statement.id] += line.amount

        for r in res:
            res[r] = round(res[r], 2)
        return res

    def button_confirm_bank(self, cr, uid, ids, context=None):
        """ Inject the statement line workflow here """
        if context is None:
            context = {}
        line_obj = self.pool.get('account.bank.statement.line')
        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(
                    cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type,
                               context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise orm.except_orm(
                    _('Configuration Error !'),
                    _('Please verify that an account is defined in the '
                      'journal.')
                )

            # protect against misguided manual changes
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise orm.except_orm(
                        _('Error !'),
                        _('The account entries lines are not in valid state.')
                    )

            line_obj.confirm(cr, uid, [line.id for line in st.line_ids],
                             context)
            st.refresh()
            self.message_post(
                cr, uid, [st.id],
                body=_('Statement %s confirmed, journal items were created.')
                % (st.name,), context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        """
        Do nothing but write the state. Delegate all actions to the statement
        line workflow instead.
        """
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Don't allow deletion of statement with confirmed bank statement lines.
        """
        if type(ids) is int:
            ids = [ids]
        for st in self.browse(cr, uid, ids, context=context):
            for line in st.line_ids:
                if line.state == 'confirmed':
                    raise orm.except_orm(
                        _('Confirmed Statement Lines'),
                        _("You cannot delete a Statement with confirmed "
                          "Statement Lines: '%s'") % st.name)
        return super(account_bank_statement, self).unlink(
            cr, uid, ids, context=context)

    _columns = {
        # override this field *only* to replace the
        # function method with the one from this module.
        # Note that it is defined twice, both in
        # account/account_bank_statement.py (without 'store') and
        # account/account_cash_statement.py (with store=True)

        'balance_end': fields.function(
            _end_balance, method=True, store=True, string='Balance'),
        }
