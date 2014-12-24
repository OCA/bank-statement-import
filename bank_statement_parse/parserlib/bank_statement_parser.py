# -*- encoding: utf-8 -*-
'''Framework for parsing bank statement import files.'''
##############################################################################
#
#  Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#  All Rights Reserved
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import re
from openerp.tools.translate import _


class BankStatementParser(object):
    '''
    A parser delivers the interface for any parser object. Inherit from
    it to implement your own.
    You should at least implement the following at the class level:
        name -> the name of the parser, shown to the user and
                    translatable.
        code -> the identifier you care to give it. Not translatable
        country_code -> the two letter ISO code of the country this parser is
                        built for: used to recreate country when new partners
                        are auto created
        doc  -> the description of the identifier. Shown to the user.
                    Translatable.

        parse -> the method for the actual parsing.
    '''
    name = None
    code = None
    country_code = None
    doc = __doc__

    def get_unique_statement_id(self, cr, base):
        name = base
        suffix = 1
        while True:
            cr.execute(
                "select id from account_bank_statement where name = %s",
                (name,))
            if not cr.rowcount:
                break
            suffix += 1
            name = "%s-%d" % (base, suffix)
        return name

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
            return re.sub('\s', '', account_no)

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

    def parse(self, cr, data):
        '''
        Parse data.

        data is a raw in memory file object. You have to split it in
        whatever chunks you see fit for parsing. It should return a list
        of BankStatement objects. Every BankStatement object
        should contain a list of BankTransaction objects.

        For identification purposes, don't invent numbering of the transaction
        numbers or bank statements ids on your own - stick with those provided
        by your bank. Doing so enables the users to re-load old transaction
        files without creating multiple identical bank statements.

        If your bank does not provide transaction ids, take a high resolution
        and a repeatable algorithm for the numbering. For example the date can
        be used as a prefix. Adding a tracer (day resolution) can create
        uniqueness. Adding unique statement ids can add to the robustness of
        your transaction numbering.

        Just mind that users can create random (file)containers with
        transactions in it. Try not to depend on order of appearance within
        these files. If in doubt: sort.
        '''
        raise NotImplementedError(
            _('This is a stub. Please implement your own.')
        )
