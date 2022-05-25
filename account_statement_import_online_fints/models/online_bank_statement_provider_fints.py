# Copyright 2022 Karolin Schlegel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime
import re

from fints.client import FinTS3PinTanClient

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OnlineBankStatementProviderFinTS(models.Model):
    _inherit = "online.bank.statement.provider"

    blz = fields.Char()


    def _init_connection(self):
        fints_connection = FinTS3PinTanClient(
            self.blz,
            self.username,
            self.password,
            self.api_base,  # ENDPOINT
            # product_id='Your product ID'
        )
        return fints_connection

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("fints", "FinTS"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "fints":
            return super()._obtain_statement_data(date_since, date_until)
        return self._fints_obtain_statement_data(date_since, date_until)

    #########
    # fints #
    #########

    def _fints_get_account_ids(self, fints_connection):
        accounts = fints_connection.get_sepa_accounts()
        return accounts

    def _fints_obtain_statement_data(self, date_since, date_until):
        """Translate information from FinTS to Odoo bank statement lines."""
        self.ensure_one()
        fints_connection = self._init_connection()
        account_ids = self._fints_get_account_ids(fints_connection)
        journal = self.journal_id
        iban = self.account_number
        account_id = None
        for account in account_ids:
            if iban == account.iban:
                 account_id = account
        if not account_id:
            raise UserError(
                _("FinTs : wrong configuration, unknown account %s")
                % journal.bank_account_id.acc_number
            )
        # FinTS can't consider future values for date_until. Therefore, we substract a second from date_until to avoid errors.
        transaction_lines = fints_connection.get_transactions(account_id, date_since, date_until-datetime.timedelta(seconds=1))
        new_transactions = []
        sequence = 0
        for transaction in transaction_lines:
            sequence += 1
            vals_line = self._fints_get_transaction_vals(transaction, sequence)
            new_transactions.append(vals_line)
        if new_transactions:
            return new_transactions, {}
        return



    def _fints_get_transaction_vals(self, transaction, sequence):
        """Translate information from FinTS to statement line vals."""
        attributes = transaction.data
        ref_list = [
            attributes[x]
            for x in {"purpose", "applicant_name", "applicant_iban"}
            if attributes[x]
        ]
        ref = " ".join(ref_list)
        date = attributes['date']
        vals_line = {
            "sequence": sequence,
            "date": date,
            "ref": re.sub(" +", " ", ref) or "/",
            "payment_ref": attributes['purpose'],
            "amount": attributes['amount'].amount,
            "unique_import_id": "{0},{1},{2},{3},{4}".format(
                date,
                attributes['amount'].amount,
                attributes['applicant_name'],
                attributes['posting_text'],
                attributes['purpose']
            ),
            "online_raw_data": attributes,
        }
        if attributes['applicant_iban']:
            vals_line["account_number"] = attributes['applicant_iban']
        if attributes['applicant_name']:
            vals_line["partner_name"] = attributes['applicant_name']
        return vals_line
