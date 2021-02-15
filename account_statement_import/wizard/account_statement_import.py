# Copyright 2004-2020 Odoo S.A.
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number

logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _name = "account.statement.import"
    _description = "Import Bank Statement Files"

    statement_file = fields.Binary(
        string="Statement File",
        required=True,
        help="Get you bank statements in electronic format from your bank "
        "and select them here.",
    )
    statement_filename = fields.Char()

    def import_file_button(self):
        """Process the file chosen in the wizard, create bank statement(s)
        and return an action."""
        self.ensure_one()
        result = {
            "statement_ids": [],
            "notifications": [],
        }
        logger.info("Start to import bank statement file %s", self.statement_filename)
        file_data = base64.b64decode(self.statement_file)
        self.import_single_file(file_data, result)
        logger.debug("result=%s", result)
        self.env["ir.attachment"].create(self._prepare_create_attachment(result))
        if self.env.context.get("return_regular_interface_action"):
            action = (
                self.env.ref("account.action_bank_statement_tree").sudo().read([])[0]
            )
            if len(result["statement_ids"]) == 1:
                action.update(
                    {
                        "view_mode": "form,tree",
                        "views": False,
                        "res_id": result["statement_ids"][0],
                    }
                )
            else:
                action["domain"] = [("id", "in", result["statement_ids"])]
        else:
            # dispatch to reconciliation interface
            lines = self.env["account.bank.statement.line"].search(
                [("statement_id", "in", result["statement_ids"])]
            )
            action = {
                "type": "ir.actions.client",
                "tag": "bank_statement_reconciliation_view",
                "context": {
                    "statement_line_ids": lines.ids,
                    "company_ids": self.env.user.company_ids.ids,
                    "notifications": result["notifications"],
                },
            }
        return action

    def _prepare_create_attachment(self, result):
        vals = {
            "name": self.statement_filename,
            # Attach to first bank statement
            "res_id": result["statement_ids"][0],
            "res_model": "account.bank.statement",
            "datas": self.statement_file,
        }
        return vals

    def import_single_file(self, file_data, result):
        parsing_data = self.with_context(active_id=self.ids[0])._parse_file(file_data)
        if not isinstance(parsing_data, list):  # for backward compatibility
            parsing_data = [parsing_data]
        logger.info(
            "Bank statement file %s contains %d accounts",
            self.statement_filename,
            len(parsing_data),
        )
        i = 0
        for single_statement_data in parsing_data:
            i += 1
            logger.debug(
                "account %d: single_statement_data=%s", i, single_statement_data
            )
            self.import_single_statement(single_statement_data, result)

    def import_single_statement(self, single_statement_data, result):
        if not isinstance(single_statement_data, tuple):
            raise UserError(
                _("The parsing of the statement file returned an invalid result.")
            )
        currency_code, account_number, stmts_vals = single_statement_data
        # Check raw data
        self._check_parsed_data(stmts_vals)
        if not currency_code:
            raise UserError(_("Missing currency code in the bank statement file."))
        # account_number can be None (example : QIF)
        currency = self._match_currency(currency_code)
        journal = self._match_journal(account_number, currency)
        if not journal.default_account_id:
            raise UserError(
                _("The Bank Accounting Account in not set on the " "journal '%s'.")
                % journal.display_name
            )
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
        # Create the bank statements
        self._create_bank_statements(stmts_vals, result)
        # Now that the import worked out, set it as the bank_statements_source
        # of the journal
        if journal.bank_statements_source != "file_import":
            # Use sudo() because only 'account.group_account_manager'
            # has write access on 'account.journal', but 'account.group_account_user'
            # must be able to import bank statement files
            journal.sudo().write({"bank_statements_source": "file_import"})

    def _parse_file(self, data_file):
        """Each module adding a file support must extends this method.
        It processes the file if it can, returns super otherwise,
        resulting in a chain of responsability.
        This method parses the given file and returns the data required
        by the bank statement import process, as specified below.
        rtype: triplet
            - currency code: string (e.g: 'EUR')
                The ISO 4217 currency code, case insensitive
            - account number: string (e.g: 'BE1234567890')
                The number of the bank account which the statement belongs to
                None if it can't be retreived from the statement file
            - bank statements data: list of dict containing
              (optional items marked by o) :
                - 'name': string (e.g: '000000123')
                - 'date': date (e.g: 2013-06-26)
                -o 'balance_start': float (e.g: 8368.56)
                -o 'balance_end_real': float (e.g: 8888.88)
                - 'transactions': list of dict containing :
                    - 'payment_ref': string (label of the line)
                    - 'date': date
                    - 'amount': float
                    - 'unique_import_id': string
                    -o 'account_number': string
                        Will be used to find/create the res.partner.bank in odoo
                    -o 'partner_name': string
        If the file is a multi-statement file, this method must return
        a list of triplets.
        """
        raise UserError(
            _(
                "This bank statement file format is not supported.\n"
                "Did you install the Odoo module to support this format?"
            )
        )

    def _check_parsed_data(self, stmts_vals):
        """ Basic and structural verifications """
        if len(stmts_vals) == 0:
            raise UserError(_("This file doesn't contain any statement."))

        no_st_line = True
        for vals in stmts_vals:
            if vals["transactions"] and len(vals["transactions"]) > 0:
                no_st_line = False
                break
        if no_st_line:
            raise UserError(_("This file doesn't contain any transaction."))

    @api.model
    def _match_currency(self, currency_code):
        currency = self.env["res.currency"].search(
            [("name", "=ilike", currency_code)], limit=1
        )
        if not currency:
            raise UserError(
                _(
                    "The bank statement file uses currency '%s' "
                    "but there is no such currency in Odoo."
                )
                % currency_code
            )
        return currency

    @api.model
    def _match_journal(self, account_number, currency):
        company = self.env.company
        journal_obj = self.env["account.journal"]
        if not account_number:  # exemple : QIF
            if not self.env.context.get("journal_id"):
                raise UserError(
                    _(
                        "The format of this bank statement file doesn't "
                        "contain the bank account number, so you must "
                        "start the wizard from the right bank journal "
                        "in the dashboard."
                    )
                )
            journal = journal_obj.browse(self.env.context.get("journal_id"))
        else:
            sanitized_account_number = sanitize_account_number(account_number)

            journal = journal_obj.search(
                [
                    ("type", "=", "bank"),
                    (
                        "bank_account_id.sanitized_acc_number",
                        "ilike",
                        sanitized_account_number,
                    ),
                ],
                limit=1,
            )

            if not journal:
                bank_accounts = self.env["res.partner.bank"].search(
                    [
                        ("partner_id", "=", company.partner_id.id),
                        ("sanitized_acc_number", "ilike", sanitized_account_number),
                    ],
                    limit=1,
                )
                if bank_accounts:
                    raise UserError(
                        _(
                            "The bank account with number '%s' exists in Odoo "
                            "but it is not set on any bank journal. You should "
                            "set it on the related bank journal. If the related "
                            "bank journal doesn't exist yet, you should create "
                            "a new one."
                        )
                        % (account_number, company.partner_id.display_name)
                    )
                else:
                    raise UserError(
                        _(
                            "Could not find any bank account with number '%s' "
                            "linked to partner '%s'. You should create the bank "
                            "account and set it on the related bank journal. "
                            "If the related bank journal doesn't exist yet, you "
                            "should create a new one."
                        )
                        % (account_number, company.partner_id.display_name)
                    )

        # We support multi-file and multi-statement in a file
        # so self.env.context.get('journal_id') doesn't mean much
        # I don't think we should really use it
        journal_currency = journal.currency_id or company.currency_id
        if journal_currency != currency:
            raise UserError(
                _(
                    "The currency of the bank statement (%s) is not the same as the "
                    "currency of the journal '%s' (%s)."
                )
                % (currency.name, journal.display_name, journal_currency.name)
            )
        return journal

    @api.model
    def _update_partner_from_account_number(self, lvals):
        partner_bank = self.env["res.partner.bank"].search(
            [("acc_number", "=", lvals["account_number"])], limit=1
        )
        if partner_bank:
            lvals["partner_bank_id"] = partner_bank.id
            lvals["partner_id"] = partner_bank.partner_id.id

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        for st_vals in stmts_vals:
            st_vals["journal_id"] = journal.id
            for lvals in st_vals["transactions"]:
                unique_import_id = lvals.get("unique_import_id")
                if unique_import_id:
                    sanitized_account_number = sanitize_account_number(account_number)
                    lvals["unique_import_id"] = (
                        (
                            sanitized_account_number
                            and sanitized_account_number + "-"
                            or ""
                        )
                        + str(journal.id)
                        + "-"
                        + unique_import_id
                    )

                if (
                    not lvals.get("partner_bank_id")
                    and lvals.get("account_number")
                    and not lvals.get("partner_id")
                ):
                    # Find the partner from his bank account number
                    # The partner selected during the
                    # reconciliation process will be linked to the bank account
                    # when the statement is closed (code in the account module)
                    self._update_partner_from_account_number(lvals)
                if not lvals.get("payment_ref"):
                    raise UserError(_("Missing payment_ref on a transaction."))
        return stmts_vals

    def _create_bank_statements(self, stmts_vals, result):
        """Create new bank statements from imported values,
        filtering out already imported transactions,
        and return data used by the reconciliation widget"""
        abs_obj = self.env["account.bank.statement"]
        absl_obj = self.env["account.bank.statement.line"]

        # Filter out already imported transactions and create statements
        statement_ids = []
        existing_st_line_ids = {}
        for st_vals in stmts_vals:
            st_lines_to_create = []
            for lvals in st_vals["transactions"]:
                existing_line = False
                if lvals.get("unique_import_id"):
                    existing_line = absl_obj.sudo().search(
                        [
                            ("unique_import_id", "=", lvals["unique_import_id"]),
                        ],
                        limit=1,
                    )
                    # we can only have 1 anyhow because we have a unicity SQL constraint
                if existing_line:
                    existing_st_line_ids[existing_line.id] = True
                    if "balance_start" in st_vals:
                        st_vals["balance_start"] += float(lvals["amount"])
                else:
                    st_lines_to_create.append(lvals)

            if len(st_lines_to_create) > 0:
                if not st_lines_to_create[0].get("sequence"):
                    for seq, vals in enumerate(st_lines_to_create, start=1):
                        vals["sequence"] = seq
                # Remove values that won't be used to create records
                st_vals.pop("transactions", None)
                # Create the statement with lines
                st_vals["line_ids"] = [[0, False, line] for line in st_lines_to_create]
                statement = abs_obj.create(st_vals)
                statement_ids.append(statement.id)

        if not statement_ids:
            raise UserError(
                _(
                    "You have already imported this file, or this file "
                    "only contains already imported transactions."
                )
            )
        result["statement_ids"].extend(statement_ids)

        # Prepare import feedback
        num_ignored = len(existing_st_line_ids)
        if num_ignored > 0:
            result["notifications"].append(
                {
                    "type": "warning",
                    "message": _(
                        "%d transactions had already been imported and were ignored."
                    )
                    % num_ignored
                    if num_ignored > 1
                    else _("1 transaction had already been imported and was ignored."),
                    "details": {
                        "name": _("Already imported items"),
                        "model": "account.bank.statement.line",
                        "ids": list(existing_st_line_ids.keys()),
                    },
                }
            )
