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
'''Define settings to be used when importing bank statements.
MAYBE MOVE TO OTHER MODULES, FOR STATEMENT RECONCILIATION???'''

from openerp.osv import orm, fields
from openerp.tools.translate import _


class BankStatementImportSettings(orm.Model):
    '''Default Journal for Bank Account'''
    _name = 'bank.statement.import.settings'
    _description = __doc__
    _rec_name = 'partner_bank_id'
    _columns = {
        'company_id': fields.many2one(
            'res.company', 'Company', select=True, required=True),
        'partner_bank_id': fields.many2one(
            'res.partner.bank', 'Bank Account', select=True, required=True),
        'journal_id': fields.many2one(
            'account.journal', 'Journal', required=True),
        'partner_id': fields.related(
            'company_id', 'partner_id',
            type='many2one', relation='res.partner',
            string='Partner'),
        'default_credit_account_id': fields.many2one(
            'account.account', 'Default credit account', select=True,
            help=('The account to use when an unexpected payment was signaled.'
                  ' This can happen when a direct debit payment is cancelled '
                  'by a customer, or when no matching payment can be found. '
                  'Mind that you can correct movements before confirming them.'
                  ),
            required=True
        ),
        'default_debit_account_id': fields.many2one(
            'account.account', 'Default debit account',
            select=True, required=True,
            help=('The account to use when an unexpected payment is received. '
                  'This can be needed when a customer pays in advance or when '
                  'no matching invoice can be found. Mind that you can '
                  'correct movements before confirming them.'
                  ),
        ),
        'costs_account_id': fields.many2one(
            'account.account', 'Bank Costs Account', select=True,
            help=('The account to use when the bank invoices its own costs. '
                  'Leave it blank to disable automatic invoice generation '
                  'on bank costs.'
                  ),
        ),
        'invoice_journal_id': fields.many2one(
            'account.journal', 'Costs Journal',
            help=('This is the journal used to create invoices for bank costs.'
                  ),
        ),
        'bank_partner_id': fields.many2one(
            'res.partner', 'Bank Partner',
            help=('The partner to use for bank costs. Banks are not partners '
                  'by default. You will most likely have to create one.'
                  ),
        ),

    }

    def _default_company(self, cr, uid, context=None):
        """
        Return the user's company or the first company found
        in the database
        """
        user = self.pool.get('res.users').read(
            cr, uid, uid, ['company_id'], context=context)
        if user['company_id']:
            return user['company_id'][0]
        return self.pool.get('res.company').search(
            cr, uid, [('parent_id', '=', False)])[0]

    def _default_partner_id(self, cr, uid, context=None, company_id=False):
        if not company_id:
            company_id = self._default_company(cr, uid, context=context)
        return self.pool.get('res.company').read(
            cr, uid, company_id, ['partner_id'],
            context=context)['partner_id'][0]

    def _default_journal(self, cr, uid, context=None, company_id=False):
        if not company_id:
            company_id = self._default_company(cr, uid, context=context)
        journal_ids = self.pool.get('account.journal').search(
            cr, uid, [('type', '=', 'bank'), ('company_id', '=', company_id)])
        return journal_ids and journal_ids[0] or False

    def _default_partner_bank_id(
            self, cr, uid, context=None, company_id=False):
        if not company_id:
            company_id = self._default_company(cr, uid, context=context)
        partner_id = self.pool.get('res.company').read(
            cr, uid, company_id, ['partner_id'],
            context=context)['partner_id'][0]
        bank_ids = self.pool.get('res.partner.bank').search(
            cr, uid, [('partner_id', '=', partner_id)], context=context)
        return bank_ids and bank_ids[0] or False

    def _default_debit_account_id(
            self, cr, uid, context=None, company_id=False):
        localcontext = context and context.copy() or {}
        localcontext['force_company'] = (
            company_id or self._default_company(cr, uid, context=context))
        account_def = self.pool.get('ir.property').get(
            cr, uid, 'property_account_receivable',
            'res.partner', context=localcontext)
        return account_def and account_def.id or False

    def _default_credit_account_id(
            self, cr, uid, context=None, company_id=False):
        localcontext = context and context.copy() or {}
        localcontext['force_company'] = (
            company_id or self._default_company(cr, uid, context=context))
        account_def = self.pool.get('ir.property').get(
            cr, uid, 'property_account_payable',
            'res.partner', context=localcontext)
        return account_def and account_def.id or False

    def find(self, cr, uid, journal_id, partner_bank_id=False, context=None):
        domain = [('journal_id', '=', journal_id)]
        if partner_bank_id:
            domain.append(('partner_bank_id', '=', partner_bank_id))
        return self.search(cr, uid, domain, context=context)

    def onchange_partner_bank_id(
            self, cr, uid, ids, partner_bank_id, context=None):
        values = {}
        if partner_bank_id:
            bank = self.pool.get('res.partner.bank').read(
                cr, uid, partner_bank_id, ['journal_id'], context=context)
            if bank['journal_id']:
                values['journal_id'] = bank['journal_id'][0]
        return {'value': values}

    def onchange_company_id(
            self, cr, uid, ids, company_id=False, context=None):
        if not company_id:
            return {}
        result = {
            'partner_id': self._default_partner_id(
                cr, uid, company_id=company_id, context=context),
            'journal_id': self._default_journal(
                cr, uid, company_id=company_id, context=context),
            'default_debit_account_id': self._default_debit_account_id(
                cr, uid, company_id=company_id, context=context),
            'default_credit_account_id': self._default_credit_account_id(
                cr, uid, company_id=company_id, context=context),
            }
        return {'value': result}

    _defaults = {
        'company_id': _default_company,
        'partner_id': _default_partner_id,
        'journal_id': _default_journal,
        'default_debit_account_id': _default_debit_account_id,
        'default_credit_account_id': _default_credit_account_id,
        'partner_bank_id': _default_partner_bank_id,
    }
