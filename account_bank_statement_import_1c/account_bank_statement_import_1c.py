# -*- coding:utf-8 -*-

from openerp import api, models
from openerp.tools.translate import _
import re
from datetime import datetime
import os


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'
    normalBegining = False
    result = {'errors': [], 'general': {}, 'remainings': {}, 'filters': {}, 'documents': []}

    @api.model
    def _parse_file(self, data_file):
        if False:
            return super(AccountBankStatementImport, self)._parse_file(data_file)
        self.normalBegining = data_file.startswith('1CClientBankExchange')
        if self.normalBegining:
            #parse general info (key=value)
            data_file = data_file.decode('cp1251').encode('utf-8')
            for key in ['ВерсияФормата', 'Кодировка', 'Отправитель', 'Получатель', 'ДатаСоздания', 'ВремяСоздания']:
                # dkey = key.decode('cp1251')
                strg = re.search(key + '=(.*)\r', data_file)
                if strg:
                    self.result['general'][key] = strg.group(1)
            # normalize
            try:
                crdate = self.result['general']['ДатаСоздания']
                self.result['general']['ДатаСоздания'] = datetime.date(datetime.strptime(crdate, '%d.%m.%Y'))
            except:
                pass
            try:
                crtime = self.result['general']['ВремяСоздания']
                self.result['general']['ДатаСоздания'] = datetime.time(datetime.strptime(crtime, '%H:%M:%S'))
            except:
                pass
            # parse remainings
            # r prefix makes this string as raw string whithout \like escapes.
            regexp_acc = r'СекцияРасчСчет([\s\S]*?)\sКонецРасчСчет'
            for match in re.findall(regexp_acc, data_file):
                for matchchild in re.findall('(.*)=(.*)\r', match):
                    self.result['remainings'][matchchild[0]] = matchchild[1]
            # normalize
            try:
                field = self.result['remainings']['ДатаНачала']
                self.result['remainings']['ДатаНачала'] = datetime.date(datetime.strptime(field, '%d.%m.%Y'))
            except:
                pass
            try:
                field = self.result['remainings']['ДатаКонца']
                self.result['remainings']['ДатаКонца'] = datetime.date(datetime.strptime(field, '%d.%m.%Y'))
            except:
                pass
            try:
                field = self.result['remainings']['НачальныйОстаток']
                self.result['remainings']['НачальныйОстаток'] = float(field)
            except:
                pass
            try:
                field = self.result['remainings']['ВсегоПоступило']
                self.result['remainings']['ВсегоПоступило'] = float(field)
            except:
                pass
            try:
                field = self.result['remainings']['ВсегоСписано']
                self.result['remainings']['ВсегоСписано'] = float(field)
            except:
                pass
            try:
                field = self.result['remainings']['КонечныйОстаток']
                self.result['remainings']['КонечныйОстаток'] = float(field)
            except:
                pass

            # parse documents
            regexp_document = r'СекцияДокумент=(.*)\s([\s\S]*?)\sКонецДокумента'
            regexp_base = '(.*)=(.*)\r'
            for matchdoc in re.findall(regexp_document, data_file):
                # document type
                document = {}
                document['Документ'] = matchdoc[0]
                for matchchild in re.findall(regexp_base, matchdoc[1]):
                    document[matchchild[0]] = matchchild[1]
                    # normalize
                try:
                    document['Номер'] = int(document['Номер'])
                except:
                    pass
                try:
                    document['Дата'] = datetime.date(datetime.strptime(document['Дата'], '%d.%m.%Y'))
                except:
                    pass
                try:
                    document['Сумма'] = float(document['Сумма'])
                except:
                    pass
                self.result['documents'].append(document)
            # make suitable for odoo format
            transactions = []
            total_amt = 0.00
            try:
                for transaction in self.result['documents']:
                    bank_account_id = partner_id = False
                    banks = self.env['res.partner.bank'].search(
                        [('acc_number', '=', transaction['ПлательщикСчет'])],
                        limit=1)  # erlier was partner name (bank_name) but i think its not good i decide use acc_number
                    if banks:
                        bank_account = banks[0]
                        bank_account_id = bank_account.id
                        partner_id = bank_account.partner_id.id
                    vals_line = {
                        'date': transaction['Дата'],
                        'name': transaction['Плательщик1'] + (
                            transaction['НазначениеПлатежа'] and ': ' + transaction['НазначениеПлатежа'] or ''),
                        'ref': transaction['ВидОплаты'],
                        # 1cCBE does not hase stuff like (transaction.id). Need to decide what to push here. Temporarry its ВидОплаты
                        'amount': transaction['Сумма'],
                        'unique_import_id': str(os.urandom(10)),  # transaction.id transaction['Номер'] if transaction['Номер'] != None else
                        # 'bank_account_id': transaction['ВидОплаты'],
                        'bank_account_id': False,
                        #'partner_id': partner_id,
                        'partner_id': False,
                    }
                    total_amt += float(transaction['Сумма'])
                    transactions.append(vals_line)
            except Exception, e:
                raise Warning(_("The following problem occurred during import. "
                                "The file might not be valid.\n\n %s" % e.message))
            vals_bank_statement = {
                'name': self.result['remainings']['РасчСчет'],  # was ofx.account.routing_number
                'transactions': transactions,
                'balance_start': self.result['remainings']['НачальныйОстаток'],
                'balance_end_real': self.result['remainings']['КонечныйОстаток']
                # was ofx.account.statement.balance + total_amt
            }
            return self.env.user.company_id.currency_id.name, self.result['remainings']['РасчСчет'], [
                vals_bank_statement]
        else:
            self.result['errors'].append('Wrong format: 1CClientBankExchange not found')
