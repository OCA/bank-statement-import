# -*- coding:utf-8 -*-
"""1C Bank import"""
from openerp import api, models
from openerp.tools.translate import _
import re
from datetime import datetime as dt
import os


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'
    normalHead = False

    @api.model
    def _parse_file(self, data_file):
        result = {'errors': [], 'general': {}, 'remain': {}, 'filters': {},
                  'documents': []}
        self.normalHead = data_file.startswith('1CClientBankExchange')
        if not self.normalHead:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        # parse general info (key=value)
        data_file = data_file.decode('cp1251').encode('utf-8')
        for key in ['ВерсияФормата', 'Кодировка', 'Отправитель',
                    'Получатель', 'ДатаСоздания', 'ВремяСоздания']:
            st = re.search(key + '=(.*)\r', data_file)
            if st:
                result['general'][key] = st.group(1)
        # normalize
        data_and_action = [
            ('ДатаСоздания', lambda y: dt.date(dt.strptime(y, '%d.%m.%Y'))),
            ('ВремяСоздания', lambda y: dt.date(dt.strptime(y, '%d.%m.%Y'))),
        ]
        for x in data_and_action:
            try:
                result['general'][x[0]] = x[1](result['general'][x[0]])
            except AttributeError:
                pass
        # parse remain
        # r prefix makes this string as raw string without \like escapes.
        regexp_acc = r'СекцияРасчСчет([\s\S]*?)\sКонецРасчСчет'
        for match in re.findall(regexp_acc, data_file):
            for match_child in re.findall('(.*)=(.*)\r', match):
                result['remain'][match_child[0]] = match_child[1]
        # normalize
        data_and_action = [
            ('ДатаНачала', lambda y: dt.date(dt.strptime(y, '%d.%m.%Y'))),
            ('ДатаКонца', lambda y: dt.date(dt.strptime(y, '%d.%m.%Y'))),
            ('НачальныйОстаток', lambda y: float(y)),
            ('ВсегоПоступило', lambda y: float(y)),
            ('ВсегоСписано', lambda y: float(y)),
            ('КонечныйОстаток', lambda y: float(y))
        ]
        for x in data_and_action:
            try:
                result['remain'][x[0]] = x[1](result['remain'][x[0]])
            except AttributeError:
                pass
        # parse documents
        regexp_document = r'СекцияДокумент=(.*)\s([\s\S]*?)' \
                          r'\sКонецДокумента'
        regexp_base = '(.*)=(.*)\r'
        for match_doc in re.findall(regexp_document, data_file):
            # document type
            document = []
            document['Документ'] = match_doc[0]
            for match_child in re.findall(regexp_base, match_doc[1]):
                document[match_child[0]] = match_child[1]
                # normalize
            try:
                document['Номер'] = int(document['Номер'])
            except AttributeError:
                pass
            try:
                document['Дата'] = dt.date(dt.strptime(
                    document['Дата'], '%d.%m.%Y'))
            except AttributeError:
                pass
            try:
                document['Сумма'] = float(document['Сумма'])
            except AttributeError:
                pass
            result['documents'].append(document)
        # make suitable for odoo format
        transactions = []
        total_amt = 0.00
        try:
            for transaction in result['documents']:
                # bank_account_id = partner_id = False
                banks = self.env['res.partner.bank'].search(
                    [('acc_number', '=', transaction['ПлательщикСчет'])],
                    limit=1)
                # earlier was partner name (bank_name) but i
                # think its not good i decide use acc_number
                if banks:
                    # bank_account = banks[0]
                    # bank_account_id = bank_account.id
                    # partner_id = bank_account.partner_id.id
                    pass
                vls_line = {
                    'date': transaction['Дата'],
                    'name': transaction['Плательщик1'] + (
                        transaction['НазначениеПлатежа'] and ': '
                        + transaction['НазначениеПлатежа'] or ''),
                    'ref': transaction['ВидОплаты'],
                    # 1cCBE does not have stuff like (transaction.id).
                    # Need to decide what to push here.
                    # Temporary its ВидОплаты
                    'amount': transaction['Сумма'],
                    'unique_import_id': str(os.urandom(10)),
                    # transaction.id transaction['Номер']
                    # if transaction['Номер'] != None else
                    # 'bank_account_id': transaction['ВидОплаты'],
                    'bank_account_id': False,
                    # 'partner_id': partner_id,
                    'partner_id': False,
                }
                total_amt += float(transaction['Сумма'])
                transactions.append(vls_line)
        except Exception, e:
            raise Warning(_("The following problem occurred "
                            "during import. "
                            "The file might not be valid.\n\n %s"
                            % e.message))
        vls_bank_statement = {
            'name': result['remain']['РасчСчет'],
            # was ofx.account.routing_number
            'transactions': transactions,
            'balance_start': result['remain']['НачальныйОстаток'],
            'balance_end_real': result['remain']['КонечныйОстаток']
            # was ofx.account.statement.balance + total_amt
        }
        return self.env.user.company_id.currency_id.name, result[
            'remain']['РасчСчет'], [vls_bank_statement]
