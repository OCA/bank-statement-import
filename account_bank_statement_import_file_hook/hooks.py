# Copyright 2023 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import base64

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.account_bank_statement_import.account_bank_statement_import import (
    AccountBankStatementImport,
)


def post_load_hook():
    def import_file_new(self):
        """ Process the file chosen in the wizard, create bank
        statement(s) and go to reconciliation. """
        if not hasattr(self, "_post_process_statements"):
            return self.import_file_original()
        self.ensure_one()
        statement_line_ids_all = []
        notifications_all = []
        # Let the appropriate implementation module parse the file and
        # return the required data
        # The active_id is passed in context in case an implementation
        # module requires information about the wizard state (see QIF)
        for data_file in self.attachment_ids:
            currency_code, account_number, stmts_vals = self.with_context(
                active_id=self.ids[0]
            )._parse_file(base64.b64decode(data_file.datas))
            # Check raw data
            self._check_parsed_data(stmts_vals, account_number)
            # Try to find the currency and journal in odoo
            currency, journal = self._find_additional_data(
                currency_code, account_number
            )
            # If no journal found, ask the user about creating one
            if not journal:
                # The active_id is passed in context so the wizard can call
                # import_file again once the journal is created
                return self.with_context(
                    active_id=self.ids[0]
                )._journal_creation_wizard(currency, account_number)
            if (
                not journal.default_debit_account_id
                or not journal.default_credit_account_id
            ):
                raise UserError(
                    _(
                        "You have to set a Default Debit Account and a Default "
                        "Credit Account for the journal: %s"
                    )
                    % (journal.name,)
                )
            # Prepare statement data to be used for bank statements creation
            stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
            # Create the bank statements
            statement_line_ids, notifications = self._create_bank_statements(stmts_vals)
            statement_line_ids_all.extend(statement_line_ids)
            notifications_all.extend(notifications)
            # START HOOK
            # Link attachment in bank statement chatter
            self._post_process_statements(data_file, statement_line_ids_all)
            # END HOOK
            # Now that the import worked out, set it as the bank_statements_source
            # of the journal
            if journal.bank_statements_source != "file_import":
                # Use sudo() because only 'account.group_account_manager'
                # has write access on 'account.journal', but 'account.group_account_user'
                # must be able to import bank statement files
                journal.sudo().bank_statements_source = "file_import"
        # Finally dispatch to reconciliation interface
        return {
            "type": "ir.actions.client",
            "tag": "bank_statement_reconciliation_view",
            "context": {
                "statement_line_ids": statement_line_ids_all,
                "company_ids": self.env.user.company_ids.ids,
                "notifications": notifications_all,
            },
        }

    if not hasattr(AccountBankStatementImport, "import_file_original"):
        AccountBankStatementImport.import_file_original = (
            AccountBankStatementImport.import_file
        )
    AccountBankStatementImport.import_file = import_file_new
