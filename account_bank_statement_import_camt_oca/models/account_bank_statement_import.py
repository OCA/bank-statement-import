# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
from io import BytesIO
import zipfile
from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""

        def _check_unique_ccy_acc_nb_sets(ccy_set, acc_nb_set):
            err_msg_dtls = []

            if len(ccy_set) > 1:
                err_msg_dtls.append(
                    _(" different currencies ({})".format(
                        ','.join(list(ccy_set))))
                )
            if len(acc_number_set) > 1:
                err_msg_dtls.append(
                    _(" different accounts:\n\t* {}".format(
                        '\n\t* '.join(list(acc_number_set))))
                )

            if len(err_msg_dtls) != 0:
                errmsg = _("This zip file contains statements for ") \
                    + " and ".join(err_msg_dtls)
                raise UserError(errmsg)

        try:
            parser = self.env['account.bank.statement.import.camt.parser']
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            try:
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    ccy_set = set()
                    acc_number_set = set()
                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        currency, account_number, new = self._parse_file(
                            data.open(member).read()
                        )
                        if currency:
                            ccy_set.add(currency)
                        if account_number:
                            acc_number_set.add(account_number)
                        transactions.extend(new)

                    # Raise error if different ccy/acc_number in zipped stmts
                    _check_unique_ccy_acc_nb_sets(ccy_set, acc_number_set)
                    currency = list(ccy_set)[0] if len(ccy_set) == 1 else None
                    account_number = list(acc_number_set)[0] if \
                        len(acc_number_set) == 1 else None
                return currency, account_number, transactions
            except (zipfile.BadZipFile, ValueError):
                pass
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.",
                          exc_info=True)
        return super(AccountBankStatementImport, self)._parse_file(data_file)
