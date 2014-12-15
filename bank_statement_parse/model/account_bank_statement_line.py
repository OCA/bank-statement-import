# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#              (C) 2011 - 2013 Therp BV (<http://therp.nl>).
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
'''
'''

from openerp.osv import orm, fields
from openerp.osv.osv import except_osv
from openerp.tools.translate import _
from openerp.addons.decimal_precision import decimal_precision as dp


class account_bank_statement_line(orm.Model):
    '''
    Extension on basic class:
        1. Extra links to account.period and res.partner.bank for tracing and
           matching.
        2. Extra 'trans' field to carry the transaction id of the bank.
        3. Readonly states for most fields except when in draft.
    '''
    _inherit = 'account.bank.statement.line'
    _description = 'Bank Transaction'

    def _get_period(self, cr, uid, date=False, context=None):
        return self.pool['account.bank.statement']._get_period(
            cr, uid, date=date, context=context)

    def _get_period_context(self, cr, uid, context=None):
        """
        Workaround for lp:1296229, context is passed positionally
        """
        return self._get_period(cr, uid, context=context)

    def _get_currency(self, cr, uid, context=None):
        '''
        Get the default currency (required to allow other modules to function,
        which assume currency to be a calculated field and thus optional)
        Remark: this is only a fallback as the real default is in the journal,
        which is inaccessible from within this method.
        '''
        res_users_obj = self.pool.get('res.users')
        return res_users_obj.browse(
            cr, uid, uid, context=context).company_id.currency_id.id

    def _get_invoice_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for st_line in self.browse(cr, uid, ids, context):
            res[st_line.id] = False
            for move_line in (
                    st_line.reconcile_id and
                    (st_line.reconcile_id.line_id or
                     st_line.reconcile_id.line_partial_ids) or
                    st_line.import_transaction_id and
                    st_line.import_transaction_id.move_line_id and
                    [st_line.import_transaction_id.move_line_id] or []):
                if move_line.invoice:
                    res[st_line.id] = move_line.invoice.id
                    continue
        return res

    def _get_link_partner_ok(
            self, cr, uid, ids, name, args, context=None):
        """
        Deliver the values of the function field that
        determines if the 'link partner' wizard is show on the
        bank statement line
        """
        res = {}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = bool(
                line.state == 'draft'
                and not line.partner_id
                and line.import_transaction_id
                and line.import_transaction_id.remote_account)
        return res

    _columns = {
        'import_transaction_id': fields.many2one(
            'banking.import.transaction',
            'Import transaction', readonly=True, ondelete='cascade'),
        'match_multi': fields.related(
            'import_transaction_id', 'match_multi', type='boolean',
            string='Multi match', readonly=True),
        'residual': fields.related(
            'import_transaction_id', 'residual', type='float',
            string='Residual', readonly=True,
            ),
        'duplicate': fields.related(
            'import_transaction_id', 'duplicate', type='boolean',
            string='Possible duplicate import', readonly=True),
        'match_type': fields.related(
            'import_transaction_id', 'match_type', type='selection',
            selection=[
                ('move', 'Move'),
                ('invoice', 'Invoice'),
                ('payment', 'Payment line'),
                ('payment_order', 'Payment order'),
                ('storno', 'Storno'),
                ('manual', 'Manual'),
                ('payment_manual', 'Payment line (manual)'),
                ('payment_order_manual', 'Payment order (manual)'),
            ],
            string='Match type', readonly=True,),
        'state': fields.selection(
            [('draft', 'Draft'), ('confirmed', 'Confirmed')], 'State',
            readonly=True, required=True),
        'parent_id': fields.many2one(
            'account.bank.statement.line',
            'Parent',
        ),
        'link_partner_ok': fields.function(
            _get_link_partner_ok, type='boolean',
            string='Can link partner'),
        }

    _defaults = {
        'state': 'draft',
        }

    def match_wizard(self, cr, uid, ids, context=None):
        res = False
        if ids:
            if isinstance(ids, (int, float)):
                ids = [ids]
            if context is None:
                context = {}
            context['statement_line_id'] = ids[0]
            wizard_obj = self.pool.get('banking.transaction.wizard')
            res_id = wizard_obj.create(
                cr, uid, {'statement_line_id': ids[0]}, context=context)
            res = wizard_obj.create_act_window(
                cr, uid, res_id, context=context
            )
        return res

    def link_partner(self, cr, uid, ids, context=None):
        """
        Get the appropriate partner or fire a wizard to create
        or link one
        """
        if not ids:
            return False

        if isinstance(ids, (int, long)):
            ids = [ids]

        # Check if the partner is already known but not shown
        # because the screen was not refreshed yet
        statement_line = self.browse(
            cr, uid, ids[0], context=context)
        if statement_line.partner_id:
            return True

        # Reuse the bank's partner if any
        if (statement_line.partner_bank_id and
                statement_line.partner_bank_id.partner_id):
            statement_line.write(
                {'partner_id': statement_line.partner_bank_id.partner_id.id})
            return True

        if (not statement_line.import_transaction_id
                or not statement_line.import_transaction_id.remote_account):
            raise orm.except_orm(
                _("Error"),
                _("No bank account available to link partner to"))

        # Check if the bank account was already been linked
        # manually to another transaction
        remote_account = statement_line.import_transaction_id.remote_account
        source_line_ids = self.search(
            cr, uid,
            [('import_transaction_id.remote_account', '=', remote_account),
             ('partner_bank_id.partner_id', '!=', False),
             ], limit=1, context=context)
        if source_line_ids:
            source_line = self.browse(
                cr, uid, source_line_ids[0], context=context)
            target_line_ids = self.search(
                cr, uid,
                [('import_transaction_id.remote_account', '=', remote_account),
                 ('partner_bank_id', '=', False),
                 ('state', '=', 'draft')], context=context)
            self.write(
                cr, uid, target_line_ids,
                {'partner_bank_id': source_line.partner_bank_id.id,
                 'partner_id': source_line.partner_bank_id.partner_id.id,
                 }, context=context)
            return True

        # Or fire the wizard to link partner and account
        wizard_obj = self.pool.get('banking.link_partner')
        res_id = wizard_obj.create(
            cr, uid, {'statement_line_id': ids[0]}, context=context)
        return wizard_obj.create_act_window(cr, uid, res_id, context=context)

    def _convert_currency(
            self, cr, uid, from_curr_id, to_curr_id, from_amount,
            round=False, date=None, context=None):
        """Convert currency amount using the company rate on a specific date"""
        curr_obj = self.pool.get('res.currency')
        if context:
            ctxt = context.copy()
        else:
            ctxt = {}
        if date:
            ctxt["date"] = date

        amount = curr_obj.compute(
            cr, uid, from_curr_id, to_curr_id, from_amount,
            round=round, context=ctxt)
        return amount

    def confirm(self, cr, uid, ids, context=None):
        """
        Create (or update) a voucher for each statement line, and then generate
        the moves by posting the voucher.
        If a line does not have a move line against it, but has an account,
        then generate a journal entry that moves the line amount to the
        specified account.
        """
        statement_pool = self.pool.get('account.bank.statement')
        obj_seq = self.pool.get('ir.sequence')
        import_transaction_obj = self.pool.get('banking.import.transaction')

        for st_line in self.browse(cr, uid, ids, context):
            if st_line.state != 'draft':
                continue
            if st_line.duplicate:
                raise orm.except_orm(
                    _('Bank transfer flagged as duplicate'),
                    _("You cannot confirm a bank transfer marked as a "
                      "duplicate (%s.%s)") %
                    (st_line.statement_id.name, st_line.name,))
            if st_line.analytic_account_id:
                if not st_line.statement_id.journal_id.analytic_journal_id:
                    raise orm.except_orm(
                        _('No Analytic Journal !'),
                        _("You have to define an analytic journal on the '%s' "
                          "journal!") % st_line.statement_id.journal_id.name
                    )
            if not st_line.amount:
                continue
            if not st_line.period_id:
                self.write(
                    cr, uid, [st_line.id], {
                        'period_id': self._get_period(
                            cr, uid, date=st_line.date, context=context)
                        })
                st_line.refresh()
            # Generate the statement number, if it is not already done
            st = st_line.statement_id
            if not st.name == '/':
                st_number = st.name
            else:
                if st.journal_id.sequence_id:
                    period = st.period_id or st_line.period_id
                    c = {'fiscalyear_id': period.fiscalyear_id.id}
                    st_number = obj_seq.next_by_id(
                        cr, uid, st.journal_id.sequence_id.id, context=c
                    )
                else:
                    st_number = obj_seq.next_by_code(
                        cr, uid, 'account.bank.statement'
                    )
                statement_pool.write(
                    cr, uid, [st.id], {'name': st_number}, context=context
                )

            if st_line.import_transaction_id:
                import_transaction_obj.confirm(
                    cr, uid, st_line.import_transaction_id.id, context)
            st_line.refresh()
            st_line_number = statement_pool.get_next_st_line_number(
                cr, uid, st_number, st_line, context)
            company_currency_id = st.journal_id.company_id.currency_id.id
            statement_pool.create_move_from_st_line(
                cr, uid, st_line.id, company_currency_id, st_line_number,
                context
            )
            self.write(
                cr, uid, st_line.id, {'state': 'confirmed'}, context)
        return True

    def cancel(self, cr, uid, ids, context=None):
        if ids and isinstance(ids, (int, float)):
            ids = [ids]
        import_transaction_obj = self.pool.get('banking.import.transaction')
        move_pool = self.pool.get('account.move')
        set_draft_ids = []
        move_unlink_ids = []
        # harvest ids for various actions
        for st_line in self.browse(cr, uid, ids, context):
            if st_line.state != 'confirmed':
                continue
            if st_line.statement_id.state != 'draft':
                raise orm.except_orm(
                    _("Cannot cancel bank transaction"),
                    _("The bank statement that this transaction belongs to "
                      "has already been confirmed"))

            if st_line.import_transaction_id:
                # Cancel transaction immediately.
                # If it has voucher, this will clean up
                # the moves on the st_line.
                import_transaction_obj.cancel(
                    cr, uid, [st_line.import_transaction_id.id],
                    context=context
                )
            st_line.refresh()
            for line in st_line.move_ids:
                # We allow for people canceling and removing
                # the associated payments, which can lead to confirmed
                # statement lines without an associated move
                move_unlink_ids.append(line.id)
            set_draft_ids.append(st_line.id)

        move_pool.button_cancel(
            cr, uid, move_unlink_ids, context=context)
        move_pool.unlink(cr, uid, move_unlink_ids, context=context)
        self.write(
            cr, uid, set_draft_ids, {'state': 'draft'}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        """
        Don't allow deletion of a confirmed statement line
        If this statement line comes from a split transaction, give the
        amount back
        """
        if type(ids) is int:
            ids = [ids]
        for line in self.browse(cr, uid, ids, context=context):
            if line.state == 'confirmed':
                raise orm.except_orm(
                    _('Confirmed Statement Line'),
                    _("You cannot delete a confirmed Statement Line"
                      ": '%s'") % line.name)
            if line.parent_id:
                line.parent_id.write(
                    {
                        'amount': line.parent_id.amount + line.amount,
                    }
                )
                line.parent_id.refresh()
        return super(account_bank_statement_line, self).unlink(
            cr, uid, ids, context=context)

    def create_instant_transaction(self, cr, uid, ids, context=None):
        """
        Check for existance of import transaction on the
        bank statement lines. Create instant items if appropriate.

        This way, the matching wizard works on manually
        encoded statements.

        The transaction is only filled with the most basic
        information. The use of the transaction at this point
        is rather to store matching data rather than to
        provide data about the transaction which have all been
        transferred to the bank statement line.
        """
        import_transaction_pool = self.pool.get('banking.import.transaction')
        if ids and isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        localcontext = context.copy()
        localcontext['transaction_no_duplicate_search'] = True
        for line in self.browse(cr, uid, ids, context=context):
            if line.state != 'confirmed' and not line.import_transaction_id:
                res = import_transaction_pool.create(
                    cr, uid, {
                        'company_id': line.statement_id.company_id.id,
                        'statement_line_id': line.id,
                        },
                    context=localcontext)
                self.write(
                    cr, uid, line.id, {
                        'import_transaction_id': res},
                    context=context)

    def split_off(self, cr, uid, ids, amount, context=None):
        """
        Create a child statement line with amount, deduce that from this line,
        change transactions accordingly
        """
        if context is None:
            context = {}

        transaction_pool = self.pool.get('banking.import.transaction')

        child_statement_ids = []
        for this in self.browse(cr, uid, ids, context):
            transaction_data = transaction_pool.copy_data(
                cr, uid, this.import_transaction_id.id
            )
            transaction_data['transferred_amount'] = amount
            transaction_data['message'] = ((transaction_data['message'] or '')
                                           + _(' (split)'))
            transaction_data['parent_id'] = this.import_transaction_id.id
            transaction_id = transaction_pool.create(
                cr,
                uid,
                transaction_data,
                context=dict(context, transaction_no_duplicate_search=True)
            )

            statement_line_data = self.copy_data(cr, uid, this.id)
            statement_line_data['amount'] = amount
            statement_line_data['name'] = (
                (statement_line_data['name'] or '') + _(' (split)'))
            statement_line_data['import_transaction_id'] = transaction_id
            statement_line_data['parent_id'] = this.id
            statement_line_id = self.create(
                cr, uid, statement_line_data, context=context)

            child_statement_ids.append(statement_line_id)
            transaction_pool.write(
                cr, uid, transaction_id, {
                    'statement_line_id': statement_line_id,
                    }, context=context)
            this.write({'amount': this.amount - amount})

        return child_statement_ids


    _columns = {
        # Redefines. Todo: refactor away to view attrs
        'amount': fields.float(
            'Amount',
            readonly=True,
            digits_compute=dp.get_precision('Account'),
            states={'draft': [('readonly', False)]},
        ),
        'ref': fields.char(
            'Ref.',
            size=32,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
        'name': fields.char(
            'Name',
            size=64,
            required=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
        'date': fields.date(
            'Date',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
        # New columns
        'trans': fields.char(
            'Bank Transaction ID',
            size=15,
            required=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
        'partner_bank_id': fields.many2one(
            'res.partner.bank',
            'Bank Account',
            required=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        ),
        'period_id': fields.many2one(
            'account.period',
            'Period',
            required=True,
            states={'confirmed': [('readonly', True)]},
        ),
        'currency': fields.many2one(
            'res.currency',
            'Currency',
            required=True,
            states={'confirmed': [('readonly', True)]},
        ),
        'reconcile_id': fields.many2one(
            'account.move.reconcile',
            'Reconciliation',
            readonly=True,
        ),
        'invoice_id': fields.function(
            _get_invoice_id,
            method=True,
            string='Linked Invoice',
            type='many2one',
            relation='account.invoice',
        ),
    }

    _defaults = {
        'period_id': _get_period_context,
        'currency': _get_currency,
    }
