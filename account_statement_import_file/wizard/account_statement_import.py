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
        required=True,
        help="Download bank statement files from your bank and upload them here.",
    )
    statement_filename = fields.Char()

    def _import_file(self):
        self.ensure_one()
        result = {
            "statement_ids": [],
            "notifications": [],  # list of text messages
        }
        logger.info("Start to import bank statement file %s", self.statement_filename)
        file_data = base64.b64decode(self.statement_file)
        self.import_single_file(file_data, result)
        logger.debug("result=%s", result)
        if not result["statement_ids"]:
            raise UserError(
                _(
                    "You have already imported this file, or this file "
                    "only contains already imported transactions."
                )
            )
        self.env["ir.attachment"].create(self._prepare_create_attachment(result))
        return result

    def import_file_button(self):
        """Process the file chosen in the wizard, create bank statement(s)
        and return an action."""
        result = self._import_file()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_bank_statement_tree"
        )
        # there is no more bank statement form view in v16
        action["domain"] = [("id", "in", result["statement_ids"])]
        if result["notifications"]:
            action_with_notif = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": True,
                    "message": "\n\n".join(result["notifications"]),
                    "next": action,
                },
            }
            return action_with_notif
        return action

    def _prepare_create_attachment(self, result):
        # Attach to first bank statement
        res_id = result["statement_ids"][0]
        st = self.env["account.bank.statement"].browse(res_id)
        vals = {
            "name": self.statement_filename,
            "res_id": res_id,
            "company_id": st.company_id.id,
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
        if not self._check_parsed_data(stmts_vals):
            return False
        if not currency_code:
            raise UserError(_("Missing currency code in the bank statement file."))
        # account_number can be None (example : QIF)
        currency = self._match_currency(currency_code)
        journal = self._match_journal(account_number, currency)
        if not journal.default_account_id:
            raise UserError(
                _("The Bank Accounting Account is not set on the journal '%s'.")
                % journal.display_name
            )
        # Prepare statement data to be used for bank statements creation
        stmts_vals = self._complete_stmts_vals(stmts_vals, journal, account_number)
        # Create the bank statements
        self._create_bank_statements(stmts_vals, result)
        # Now that the import worked out, set it as the bank_statements_source
        # of the journal
        if journal.bank_statements_source != "file_import_oca":
            # Use sudo() because only 'account.group_account_manager'
            # has write access on 'account.journal', but 'account.group_account_user'
            # must be able to import bank statement files
            journal.sudo().write({"bank_statements_source": "file_import_oca"})

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
        """
        Basic and structural verifications.
        Return False when empty data (don't raise en error, because we
        support multi-statement files and we don't want one empty
        statement to block the import of others)
        """
        if len(stmts_vals) == 0:
            return False

        no_st_line = True
        for vals in stmts_vals:
            if vals["transactions"] and len(vals["transactions"]) > 0:
                no_st_line = False
                break
        if no_st_line:
            return False
        return True

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
            ctx_journal_id = self.env.context.get("journal_id")
            if journal and ctx_journal_id and journal.id != ctx_journal_id:
                ctx_journal = journal_obj.browse(ctx_journal_id)
                raise UserError(
                    _(
                        "The journal found for the file (%(journal_match)s) is "
                        "different from the selected journal (%(journal_selected)s).",
                        journal_match=journal.display_name,
                        journal_selected=ctx_journal.display_name,
                    )
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
                            "The bank account with number '%(account_number)s' exists in Odoo "
                            "but it is not set on any bank journal. You should "
                            "set it on the related bank journal. If the related "
                            "bank journal doesn't exist yet, you should create "
                            "a new one.",
                            account_number=account_number,
                        )
                    )
                else:
                    raise UserError(
                        _(
                            "Could not find any bank account with number '%(account_number)s' "
                            "linked to partner '%(partner_name)s'. You should create the bank "
                            "account and set it on the related bank journal. "
                            "If the related bank journal doesn't exist yet, you "
                            "should create a new one.",
                            account_number=account_number,
                            partner_name=company.partner_id.display_name,
                        )
                    )

        # We support multi-file and multi-statement in a file
        # so self.env.context.get('journal_id') doesn't mean much
        # I don't think we should really use it
        journal_currency = journal.currency_id or company.currency_id
        if journal_currency != currency:
            raise UserError(
                _(
                    "The currency of the bank statement (%(currency_name)s) "
                    "is not the same as the currency of the journal "
                    "'%(journal_name)s' (%(journal_currency_name)s).",
                    currency_name=currency.name,
                    journal_name=journal.display_name,
                    journal_currency_name=journal_currency.name,
                )
            )
        return journal

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        speeddict = journal._statement_line_import_speeddict()
        for st_vals in stmts_vals:
            st_vals["journal_id"] = journal.id
            for lvals in st_vals["transactions"]:
                lvals["journal_id"] = journal.id
                journal._statement_line_import_update_unique_import_id(
                    lvals, account_number
                )
                journal._statement_line_import_update_hook(lvals, speeddict)
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
            return False
        result["statement_ids"].extend(statement_ids)

        # Prepare import feedback
        num_ignored = len(existing_st_line_ids)
        if num_ignored > 0:
            if num_ignored == 1:
                msg = _("1 transaction had already been imported and was ignored.")
            else:
                msg = (
                    _("%d transactions had already been imported and were ignored.")
                    % num_ignored
                )
            result["notifications"].append(msg)
