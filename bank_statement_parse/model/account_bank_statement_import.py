# -*- coding: utf-8 -*-
"""Extend account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
import base64
from StringIO import StringIO
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2
from openerp import models
from openerp.tools.translate import _


class AccountBankStatementImport(models.TransientModel):
    """Import Bank Statements File."""
    _inherit = 'account.bank.statement.import'
    _description = __doc__

    def convert_transaction(
            self, cr, uid, transaction, context=None):
        """Convert transaction object to values for create."""
        partner_vals = {
            'name': transaction.remote_owner,
        }
        bank_vals = {
            'acc_number': transaction.remote_account,
            'owner_name': transaction.remote_owner,
            'street': transaction.remote_owner_address,
            'city': transaction.remote_owner_city,
            'zip': transaction.remote_owner_postalcode,
            'country_code': transaction.remote_owner_country_code,
            'bank_bic': transaction.remote_bank_bic,
        }
        bank_account_id, partner_id = self.detect_partner_and_bank(
            cr, uid, transaction_vals=None, partner_vals=partner_vals,
            bank_vals=bank_vals, context=context
        )
        vals_line = {
            'date': transaction.value_date,
            'name': (
                transaction.message or transaction.eref or
                transaction.remote_owner or ''),  # name is required
            'ref': transaction.eref,
            'amount': transaction.transferred_amount,
            'partner_name': transaction.remote_owner,
            'acc_number': transaction.remote_account,
            'partner_id': partner_id,
            'bank_account_id': bank_account_id,
            'unique_import_id': transaction.transaction_id,
        }
        return vals_line

    def convert_statements(
            self, cr, uid, os_statements, context=None):
        """Taking lots of code from the former import wizard, convert array
        of BankStatement objects to values that can be used in create of
        bank.statement model, including bank.statement.line tuple."""
        # os_ = old style
        # ns_ = new style
        ns_statements = []
        for statement in os_statements:
            # Set statement_data
            ns_statement = dict(
                acc_number=statement.local_account,
                name=statement.statement_id,
                date=statement.date.strftime('%Y-%m-%d'),
                balance_start=statement.start_balance,
                balance_end_real=statement.end_balance,
                balance_end=statement.end_balance,
                state='draft',
                user_id=uid,
            )
            ns_transactions = []
            subno = 0
            for transaction in statement.transactions:
                subno += 1
                if not transaction.transaction_id:
                    transaction.transaction_id = (
                        statement.statement_id + str(subno).zfill(4))
                ns_transactions.append(
                    self.convert_transaction(
                        cr, uid, transaction, context=context))
            ns_statement['transactions'] = ns_transactions
            ns_statements.append(ns_statement)
        return ns_statements

    def create_bank_account(
            self, cr, uid, acc_number, bank_vals=None, context=None):
        """Create bank-account, with type determined from acc_number."""
        if not acc_number:
            return False
        bank_vals = dict(bank_vals or {})
        bank_model = self.pool['res.partner.bank']
        country_model = self.pool['res.country']
        # Create the bank account, not linked to any partner.
        # The reconciliation will link the partner manually
        # chosen at the bank statement final confirmation time.
        if bank_model.is_iban_valid(
                cr, uid, acc_number, context=context):
            bank_code = 'iban'
        else:
            bank_code = 'bank'
        bank_vals.update({
            'acc_number': acc_number,
            'state': bank_code,
        })
        # Try to find country, if passed
        if 'country_code' in bank_vals:
            country_code = bank_vals['country_code']
            if country_code:  # Might be False
                country_ids = country_model.search(
                    cr, uid, [('code', '=', country_code.upper())],
                    context=context
                )
                if country_ids:
                    bank_vals['country_id'] = country_ids[0]
            del bank_vals['country_code']  # Not in model
        return bank_model.create(
            cr, uid, bank_vals, context=context)

    def detect_partner_and_bank(
            self, cr, uid, transaction_vals=None, partner_vals=None,
            bank_vals=None, context=None):
        """Try to find a partner and bank_account for a transaction.

        The calling function has to pass all the information it can gather
        from the imported transaction. This function will try several
        searches to find an existing bank account and partner. But possibly
        only the partner is found. In that case, a bank account might be
        automatically created if the information is there, and it is certain
        the transaction can not be for one of the existing bank accounts of
        the partner.

        The following searches will be done (if needed information present):
        - Search on bank account number;
        - Search on partner name and address info;  # NOT IMPLEMENTED
        - Search only on partner name (should be unique);
        - Search only on address info (should be unique and complete enough);
          # NOT IMPLEMENTED
        - Search invoices and moves with eref info (should be unique).
          # NOT IMPLEMENTED
        """
        partner_id = False
        bank_account_id = False
        bank_model = self.pool['res.partner.bank']
        partner_model = self.pool['res.partner']
        acc_number = (
            'acc_number' in bank_vals and bank_vals['acc_number'] or False)
        acc_name = (
            'acc_name' in partner_vals and partner_vals['acc_name'] or False)
        # Search on bank account number
        if acc_number:
            ids = bank_model.search(
                cr, uid, [('acc_number', '=', acc_number)], context=context)
            if ids:
                # Bank accounts should be unique!
                assert len(ids) == 1, (_(
                    'More then one bank account with number %s!'
                ) % acc_number)
                bank_account_id = ids[0]
                bank_records = bank_model.read(
                    cr, uid, ids, ['partner_id'], context=context)
                # Bank account might not be linked to partner yet:
                if bank_records[0]['partner_id']:
                    partner_id = bank_records[0]['partner_id'][0]
            else:
                bank_account_id = self.create_bank_account(
                    cr, uid, acc_number, bank_vals=bank_vals, context=context)
        # Search on partner data
        if (not partner_id) and acc_name:
            ids = partner_model.search(
                cr, uid, [('name', '=', acc_name)], context=context
            )
            if len(ids) == 1:
                # TODO Should warn or raise if > 1
                partner_id = ids[0]
                # If we found a partner now, and we had a bank account
                # withouth partner, then link the two now:
                if bank_account_id:
                    bank_model.write(
                        cr, uid, [bank_account_id],
                        {'partner_id': partner_id}, context=context
                    )
        return bank_account_id, partner_id

    def _complete_statements(self, cr, uid, statements, context=None):
        """Complete statements and transactions."""
        journal_model = self.pool['account.journal']
        bank_model = self.pool['res.partner.bank']
        currency_model = self.pool['res.currency']
        for st_vals in statements:
            # Make sure we have a journal_id:
            journal_id = (
                'journal_id' in st_vals and st_vals['journal_id'] or False)
            journal_id = journal_id or context.get('journal_id', False)
            # Resolve bank-information for statement, if present
            # In theory we might just have the journal.
            bank_obj = False
            acc_number = (
                'acc_number' in st_vals and st_vals.pop('acc_number') or False
            )
            bank_account_id = (
                'bank_account_id' in st_vals and st_vals['bank_account_id'] or
                False
            )
            if not bank_account_id and acc_number:
                ids = bank_model.search(
                    cr, uid, [('acc_number', '=', acc_number)],
                    context=context
                )
                if ids:
                    # Bank accounts should be unique!
                    if len(ids) > 1:
                        raise Warning(_(
                            'More then one bankaccount with number %s!'
                        ) % acc_number)
                    bank_account_id = ids[0]
                else:
                    raise Warning(_(
                        'No bankaccount with number %s!'
                    ) % acc_number)
            if bank_account_id:
                bank_obj = bank_model.browse(
                    cr, uid, bank_account_id, context=context)
                acc_number = acc_number or bank_obj.acc_number
                if not bank_obj.journal_id:
                    raise Warning(_(
                        'Bankaccount %s not linked to journal!'
                    ) % bank_obj.acc_number)
                if journal_id:
                    if bank_obj.journal_id.id != journal_id:
                        raise Warning(_(
                            'The account of this statement is linked to'
                            ' another journal.'
                        ))
                else:
                    journal_id = bank_obj.journal_id.id
            # By now we should know a journal_id:
            if not journal_id:
                raise Warning(_(
                    'Cannot find in which journal to import this statement.'
                    'Please manually select a journal.'
                ))
            # If a currency_code was specified, it should be equal to the
            # journal currency, if provided, or else to the company currency:
            if 'currency_code' in st_vals:
                currency_code = st_vals['currency_code']
                currency_ids = currency_model.search(
                    cr, uid, [('name', '=ilike', currency_code)],
                    context=context
                )
                if not currency_ids:
                    raise Warning(_(
                        'Unknown currency %s specified in import!'
                    ) % currency_code)
                compare_currency_id = False
                journal_obj = journal_model.browse(
                    cr, uid, journal_id, context=context)
                if journal_obj.currency:
                    compare_currency_id = journal_obj.currency.id
                else:
                    company_obj = self.pool['res.users'].browse(
                        cr, uid, uid, context=context).company_id
                    if company_obj.currency:
                        compare_currency_id = company_obj.currency.id
                # If importing into an existing journal, its currency must be
                # the same as the bank statement
                if (compare_currency_id and
                        compare_currency_id != currency_ids[0]):
                    raise Warning(_(
                        'The currency of the bank statement is not the same'
                        ' as the currency of the journal !'
                    ))
            st_vals['journal_id'] = journal_id
            # Now complete all transactions in a single statement:
            for line_vals in st_vals['transactions']:
                unique_import_id = line_vals.get('unique_import_id', False)
                if unique_import_id:
                    line_vals['unique_import_id'] = (
                        (acc_number and acc_number + '-' or '') +
                        unique_import_id
                    )
                if ('bank_account_id' not in line_vals or
                        not line_vals['bank_account_id']):
                    partner_vals = {
                        'name': line_vals.get('partner_name', False),
                    }
                    bank_vals = {
                        'acc_number': line_vals.get('acc_number', False),
                        'owner_name': line_vals.get('partner_name', False),
                    }
                    bank_account_id, partner_id = (
                        self.detect_partner_and_bank(
                            cr, uid, transaction_vals=None,
                            partner_vals=partner_vals, bank_vals=bank_vals,
                            context=context
                        )
                    )
                    line_vals['partner_id'] = partner_id
                    line_vals['bank_account_id'] = bank_account_id
                if 'acc_number' in line_vals:
                    del line_vals['acc_number']
        return statements

    def import_file(self, cr, uid, ids, context=None):
        """
        Improve base import.

        - Process archive files (zip);
        - Support multiple bank-accounts per import file;
        - No automatic creation of journals of company bank-accounts;
        - Use all information in transaction when creating partner bank
            account

        This method is based on the following assumptions or preconditions.
        - Only statements for already created company bank accounts are
          processed.
        - Each company bank account must have an associated journal.
        - The currency for the journal must be specified, and should be
          consistent with the currency for the bank statement, if present
          in that statement.
        """
        if context is None:
            context = {}
        # Set the active_id in the context, so any extension module can
        # reuse the fields chosen in the wizard if needed
        # (see .QIF for example):
        context.update({'active_id': ids[0]})

        this_obj = self.browse(cr, uid, ids[0], context=context)
        data = base64.b64decode(this_obj.data_file)
        files = [data]
        try:
            with ZipFile(StringIO(data), 'r') as archive:
                files = [
                    archive.read(filename) for filename in archive.namelist()
                    if not filename.endswith('/')
                    ]
        except BadZipfile:
            pass

        # Parse the file(s)
        statements = []
        for import_file in files:
            # The appropriate implementation module returns the required data
            parse_result = self._parse_file(
                cr, uid, import_file, context=context)
            # Parse result might be a tuple, containing currency,
            # account number and statements. Or it might just contain
            # a list of statements. The first case will be morphed into the
            # second case, to allow for simple further processing.
            if (len(parse_result) == 3 and
                    isinstance(parse_result[0], basestring) and
                    isinstance(parse_result[1], basestring) and
                    isinstance(parse_result[2], (list, tuple))):
                for stmt in parse_result[2]:
                    stmt['currency_code'] = parse_result[0]
                    stmt['acc_number'] = parse_result[1]
                    statements += [stmt]
            else:
                statements += parse_result
        # Check raw data
        self._check_parsed_data(
            cr, uid, statements, context=context)
        # Prepare statement data to be used for bank statements creation
        statements = self._complete_statements(
            cr, uid, statements, context=context)
        # Create the bank statements
        statement_ids, notifications = self._create_bank_statements(
            cr, uid, statements, context=context)
        # Finally dispatch to reconciliation interface
        model, action_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'account', 'action_bank_reconcile_bank_statements')
        action = self.pool[model].browse(cr, uid, action_id, context=context)
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
