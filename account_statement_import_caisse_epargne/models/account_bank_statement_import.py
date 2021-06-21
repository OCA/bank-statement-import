import datetime
import logging
import re

from odoo import api, models
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    regexp_version = {
        'version_A': {
            'line_1': r"Code de la banque : (?P<bank_group_code>\d{5});"
                      r"Code de l'agence : (?P<bank_local_code>\d{5});"
                      "Date de début de téléchargement : "
                      r"(?P<opening_date>r'\d{2}/r'\d{2}/\d{4});"
                      "Date de fin de téléchargement : "
                      r"(?P<closing_date>\d{2}/\d{2}/\d{4});;$",
            'line_2': r"^Numéro de compte : (?P<bank_account_number>\d{11})"
                      ";Nom du compte : (?P<bank_account_name>.*);"
                      "Devise : (?P<currency>.{3});;;$",
            'line_closing_balance': r"^Solde en fin de période;;;;"
                                    r"(?P<balance>\d+(,\d{1,2})?);$",
            'line_opening_balance': "^Solde en début de période;;;;"
                                    r"(?P<balance>\d+(,\d{1,2})?);$",
            'line_credit': r"^(?P<date>\d{2}/\d{2}/\d{4});"
                           "(?P<unique_import_id>.*);(?P<name>.*);;"
                           r"(?P<credit>\d+(,\d{1,2})?);(?P<note>.*)$",
            'line_debit': r"^(?P<date>\d{2}/\d{2}/\d{4});"
                          "(?P<unique_import_id>.*);(?P<name>.*);"
                          r"(?P<debit>-\d+(,\d{1,2})?);;(?P<note>.*)$",
            'line_date_format': '%d/%m/%Y',
        },
        'version_B': {
            'line_1': r"^Code de la banque : (?P<bank_group_code>\d{5})"
                      ";Date de début de téléchargement : "
                      r"(?P<opening_date>\d{2}/\d{2}/\d{4});"
                      "Date de fin de téléchargement : "
                      r"(?P<closing_date>\d{2}/\d{2}/\d{4});;$",
            'line_2': "^Numéro de compte : "
                      r"(?P<bank_account_number>\d{11});Devise :"
                      r" (?P<currency>.{3});;;$",
            'line_closing_balance': "^Solde en fin de période;;;"
                                    r"(?P<balance>\d+(,\d{1,2})?);$",
            'line_opening_balance': "^Solde en début de période;;;"
                                    r"(?P<balance>\d+(,\d{1,2})?);$",
            'line_credit': r"^(?P<date>\d{2}/\d{2}/\d{4});(?P<name>.*);;"
                           r"(?P<credit>\d+(,\d{1,2})?);(?P<note>.*)$",
            'line_debit': r"^(?P<date>\d{2}/\d{2}/\d{4});(?P<name>.*);"
                          r"(?P<debit>-\d+(,\d{1,2})?);;(?P<note>.*)$",
            'line_date_format': '%d/%m/%Y',
        },
        'version_C': {
            'line_1': r"^Code de la banque : (?P<bank_group_code>\d{5});"
                      r"Code de l'agence : (?P<bank_local_code>\d{5});"
                      "Date de début de téléchargement : "
                      r"(?P<opening_date>\d{2}/\d{2}/\d{4});"
                      "Date de fin de téléchargement : "
                      r"(?P<closing_date>\d{2}/\d{2}/\d{4});$",
            'line_2': r"^Numéro de compte : (?P<bank_account_number>\d{11})"
                      ";Nom du compte : (?P<nom_compte>.*);"
                      "Devise : (?P<currency>.{3});$",
            'line_closing_balance': "^Solde en fin de période;;;;"
                                    r"(?P<balance>(\+|-)?\d+(,\d{1,2})?)$",
            'line_opening_balance': "^Solde en début de période;;;;"
                                    r"(?P<balance>(\+|-)?\d+(,\d{1,2})?)$",
            'line_credit': r"^(?P<date>\d{2}/\d{2}/\d{2});(?P<ref>.*);"
                           r"(?P<name>.*);;\+(?P<credit>\d+(,\d{1,2})?)"
                           ";(?P<note>.*);$",
            'line_debit': r"^(?P<date>\d{2}/\d{2}/\d{2});"
                          "(?P<ref>.*);(?P<name>.*);"
                          r"(?P<debit>-\d+(,\d{1,2})?);;(?P<note>.*);$",
            'line_date_format': '%d/%m/%y',
        }
    }

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number and len(account_number) > 4:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', account_number)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id
        return bank_account_id

    @api.model
    def _check_file(self, data_file):
        try:
            file_version = "version_A"
            # for files generated before june 2017
            test_versionA = re.compile(
                self.regexp_version[file_version]['line_1']
            ).search(data_file[0])
            if (not test_versionA):
                # for files generated after june 2017 and before decembre 2017
                file_version = "version_B"
                test_versionB = re.compile(
                    self.regexp_version[file_version]['line_1']
                ).search(data_file[0])
                if (not test_versionB):
                    # for files generated after december 2017
                    file_version = "version_C"

            parse_line_1 = re.compile(
                self.regexp_version[file_version]['line_1']
            ).search(data_file[0])
            bank_group_code = parse_line_1.group('bank_group_code')
            openning_date = parse_line_1.group('opening_date')
            closing_date = parse_line_1.group('closing_date')

            parse_line_2 = re.compile(
                self.regexp_version[file_version]['line_2']
            ).search(data_file[1])
            bank_account_number = parse_line_2.group('bank_account_number')
            currency = parse_line_2.group('currency')

            closing_balance = float(
                re.compile(
                    self.regexp_version[file_version]['line_closing_balance']
                ).search(data_file[3]).group('balance').replace(',', '.'))
            opening_balance = float(
                re.compile(
                    self.regexp_version[file_version]['line_opening_balance']
                ).search(data_file[len(data_file) - 1]
                         ).group('balance').replace(',', '.'))
        except Exception as e:
            _logger.debug(e)
            return False
        return (
            file_version,
            bank_group_code,
            openning_date,
            closing_date,
            bank_account_number,
            opening_balance,
            closing_balance,
            currency
        )

    @api.model
    def _parse_file(self, data_file):
        data_file = data_file.decode('cp1252')
        data_file = data_file.splitlines()
        result = self._check_file(data_file)
        if not result:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        file_version, bank_group_code, openning_date,\
            closing_date, bank_account_number,\
            opening_balance, closing_balance, currency = result
        transactions = []
        total_amt = 0.00
        try:
            index = 0
            for line in data_file[5:len(data_file) - 1]:
                transaction = re.compile(
                    self.regexp_version[file_version]['line_debit']
                ).search(line)
                if (transaction):
                    transaction_amount = float(
                        transaction.group('debit').replace(',', '.')
                    )
                else:
                    transaction = re.compile(
                        self.regexp_version[file_version]['line_credit']
                    ).search(line)
                    transaction_amount = float(
                        transaction.group('credit').replace(',', '.')
                    )

                libelle = transaction.group('name')
                if transaction.group('note') != "":
                    libelle += " */* " + transaction.group('note')
                vals_line = {
                    'date': datetime.datetime.strptime(
                        transaction.group('date'),
                        self.regexp_version[file_version]['line_date_format']
                    ).strftime(DEFAULT_SERVER_DATE_FORMAT),
                    'name': libelle,
                    # 'ref': transaction.group('unique_import_id'),
                    'amount': transaction_amount,
                    # 'note': transaction.group('note'),
                    'unique_import_id': str(index) +
                    transaction.group('date') +
                    transaction.group('name') +
                    str(transaction_amount) + transaction.group('note'),
                    'account_number': bank_account_number,
                    'partner_id': False,
                    'bank_account_id': self._find_bank_account_id(bank_account_number),
                }
                total_amt += transaction_amount
                transactions.append(vals_line)
                index = index + 1

            if (abs(opening_balance + total_amt - closing_balance) > 0.00001):
                raise ValueError(_(
                    "Sum of opening balance and transaction "
                    "lines is not equel to closing balance."))

        except Exception as e:
            raise Warning(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s" % e.message))

        vals_bank_statement = {
            'name': bank_account_number + "/" + openning_date,
            'date': datetime.datetime.strptime(
                openning_date, '%d/%m/%Y'
            ).strftime(DEFAULT_SERVER_DATE_FORMAT),
            'transactions': list(reversed(transactions)),
            'balance_start': opening_balance,
            'balance_end_real': closing_balance,
        }
        return currency, bank_account_number, [vals_bank_statement]
