# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
from io import BytesIO
import zipfile
from odoo import api, models
from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _xml_split_file(self, data_file):
        """BNP France is known to merge xml files"""
        if not data_file.startswith(b'<?xml'):
            return [data_file]
        data_file_elements = []
        all_files = data_file.split(b'<?xml')
        for file in all_files:
            if file:
                data_file_elements.append(b'<?xml' + file)
        return data_file_elements

    @api.model
    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        try:
            parser = self.env['account.bank.statement.import.camt.parser']
            _logger.debug("Try parsing with camt.")
            currency = None
            account_number = None
            transactions = []
            data_file_elements = self._xml_split_file(data_file)
            for data_file_element in data_file_elements:
                currency, account_number, element_transactions = parser.parse(
                    data_file_element
                )
                transactions.extend(element_transactions)
            return currency, account_number, transactions
        except ValueError:
            try:
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    journal_account_number = None
                    journal_currency_name = None
                    if self.env.context.get('journal_id', None):
                        journal_id = self.env.context.get('journal_id', None)
                        journal = self.env['account.journal'].browse(
                            journal_id
                        )
                        journal_account_number = sanitize_account_number(
                            journal.bank_account_id.acc_number
                        )
                        journal_currency_name = journal.currency_id.name

                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        old_account_number = account_number
                        old_currency = currency
                        currency, account_number, new = self._parse_file(
                            data.open(member).read()
                        )
                        if (
                            journal_account_number
                            and journal_account_number != account_number
                        ):
                            continue
                        if (
                            not journal_account_number
                            and old_account_number
                            and old_account_number != account_number
                        ):
                            raise ValueError(
                                'File containing statements for multiple '
                                'accounts'
                            )
                        if (
                            journal_currency_name
                            and journal_currency_name != currency
                        ):
                            continue
                        if (
                            not journal_currency_name
                            and old_currency
                            and old_currency != currency
                        ):
                            raise ValueError(
                                'File containing statements for multiple '
                                'currencies'
                            )
                        transactions.extend(new)
                    return currency, account_number, transactions
            except (zipfile.BadZipFile, ValueError):
                pass
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.",
                          exc_info=True)
        return super(AccountBankStatementImport, self)._parse_file(data_file)
