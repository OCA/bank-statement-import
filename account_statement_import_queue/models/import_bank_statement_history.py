# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import ast
import base64
import json
import logging
import traceback
from datetime import date, datetime
from io import StringIO
from typing import Any

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.tools import split_every

from odoo.addons.queue_job.delay import chain

from ..exception import ImportBankStatementDataError

_logger = logging.getLogger(__name__)


class ImportBankStatementHistory(models.Model):
    _name = "import.bank.statement.history"
    _inherit = ["mail.thread"]
    _description = "Import Bank Statement History"

    name = fields.Char(tracking=True)
    import_attachment_id = fields.Many2one(
        "ir.attachment", string="Import File", tracking=True, index=True
    )
    res_model = fields.Char(string="Resource Model", tracking=True)
    res_ids = fields.Char(string="Resource IDs", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("importing_data", "Importing Data"),
            ("import_data_error", "Import Data Error"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        index=True,
    )
    context = fields.Json(default=lambda self: self.env.context or {})
    context_text = fields.Text(
        string="Context(as text)",
        compute="_compute_context_text",
        store=True,
    )
    result = fields.Text(readonly=True)
    exc_name = fields.Char(string="Exception", readonly=True)
    exc_message = fields.Char(string="Exception Message", readonly=True, tracking=True)
    exc_info = fields.Text(string="Exception Info", readonly=True)
    queue_job_ids = fields.Many2many(
        "queue.job",
        "import_bank_statement_history_queue_job_rel",  # Custom relation table name
        "import_bank_statement_history_id",
        "job_id",
        string="Queue Jobs",
    )
    journal_id = fields.Many2one("account.journal", index=True)
    sheet_mapping_id = fields.Many2one(
        string="Sheet mapping",
        comodel_name="account.statement.import.sheet.mapping",
        index=True,
    )
    import_json_data = fields.Json(
        default=(
            {
                "parsed_statement_data": [],
                "prepared_statement_data_for_import": [],
                "statement_ids": [],
                "notifications": [],
                "statement_creation_data": {},
            }
        )
    )
    import_json_data_text = fields.Text(
        string="Import JSON Data(as text)",
        compute="_compute_import_json_data_text",
        store=True,
    )

    @api.depends("import_json_data")
    def _compute_import_json_data_text(self) -> None:
        """Compute text representation of import JSON data."""
        for rec in self:
            rec.import_json_data_text = (
                json.dumps(rec.import_json_data, indent=2)
                if rec.import_json_data
                else ""
            )

    @api.depends("context")
    def _compute_context_text(self) -> None:
        """Compute text representation of context."""
        for rec in self:
            rec.context_text = json.dumps(rec.context, indent=2) if rec.context else ""

    def update_state(self, state: str) -> None:
        """Update record state with validation."""
        self.ensure_one()
        self.state = state

    def _get_failure_values(
        self, traceback_txt: str, orig_exception: Exception
    ) -> dict[str, str]:
        """Build failure values dictionary from exception."""
        exception_name = orig_exception.__class__.__name__
        if hasattr(orig_exception, "__module__"):
            exception_name = f"{orig_exception.__module__}.{exception_name}"
        exc_message = getattr(orig_exception, "name", str(orig_exception))
        return {
            "exc_info": traceback_txt,
            "exc_name": exception_name,
            "exc_message": exc_message,
        }

    def _get_queue_job_recs(self, job: Any) -> models.Model:
        # This method must be called after delay()
        return (
            self.env["queue.job"]
            .sudo()
            .search([("graph_uuid", "=", job._generated_job.graph_uuid)])
        )

    def _handle_import_error(self, orig_exception: Exception) -> None:
        self.env.cr.rollback()
        with StringIO() as buff:
            traceback.print_exc(file=buff)
            traceback_txt = buff.getvalue()
            _logger.error(traceback_txt)
        with Registry(self.env.cr.dbname).cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            new_import_bank_statement_history_rec = self.with_env(new_env)
            # Use sudo and disable tracking to avoid fetching large fields
            # during access checks and change tracking
            new_import_bank_statement_history_rec.sudo().with_context(
                tracking_disable=True
            ).write(self._get_failure_values(traceback_txt, orig_exception))
            new_import_bank_statement_history_rec.sudo().update_state(
                "import_data_error"
            )
            new_import_bank_statement_history_rec.sudo()._perform_cleanup()

    def _perform_cleanup(self) -> None:
        """Cleanup empty bank statements and update result."""
        _logger.info(
            "Performing cleanup: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )
        import_json_data_dict = self.import_json_data
        statement_ids = import_json_data_dict.get("statement_ids", [])
        if not statement_ids:
            return

        # Find statements that have lines
        groups = self.env["account.bank.statement.line"].read_group(
            domain=[("statement_id", "in", statement_ids)],
            fields=["statement_id"],
            groupby=["statement_id"],
        )
        statements_with_lines = {
            g["statement_id"][0] for g in groups if g.get("statement_id")
        }

        # Identify statements to delete (those without lines)
        statements_to_delete = set(statement_ids) - statements_with_lines

        if statements_to_delete:
            statements_to_delete = tuple(statements_to_delete)
            _logger.info(
                "Deleting Bank Statements: %(bank_statement_ids)s",
                {"bank_statement_ids": ",".join(map(str, statements_to_delete))},
            )
            try:
                self.env["account.bank.statement"].browse(
                    statements_to_delete
                ).sudo().unlink()
                _logger.info(
                    "Deleted Bank Statements: %(bank_statement_ids)s",
                    {"bank_statement_ids": ",".join(map(str, statements_to_delete))},
                )
            except Exception:
                _logger.error(
                    "Error deleting Bank Statements: %(bank_statement_ids)s",
                    {"bank_statement_ids": ",".join(map(str, statements_to_delete))},
                    exc_info=True,
                )

            self.res_ids = ",".join(map(str, statements_with_lines))

            if self.result:
                try:
                    result_dict = ast.literal_eval(self.result)
                    result_dict["ids"] = list(statements_with_lines)
                    self.result = str(result_dict)
                except (ValueError, SyntaxError) as e:
                    _logger.warning("Could not parse result field: %s", e)

            import_json_data_dict["statement_ids"] = list(statements_with_lines)
            self.import_json_data = import_json_data_dict
        _logger.info(
            "Performed cleanup successfully: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def parse_statement_data(self) -> None:
        def serialize(obj: Any) -> Any:
            if isinstance(obj, date | datetime):
                return obj.isoformat()
            return obj

        try:
            _logger.info(
                "Parsing bank statement file: %(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = {
                "parsed_statement_data": [],
                "prepared_statement_data_for_import": [],
            }
            account_statement_import_wizard_id = self.env[
                "account.statement.import"
            ].create(
                {
                    "journal_id": self.journal_id.id,
                    "sheet_mapping_id": self.sheet_mapping_id.id,
                    "statement_file": self.import_attachment_id.datas,
                    "statement_filename": self.name,
                }
            )
            if account_statement_import_wizard_id:
                # Parse the file
                parsing_data = account_statement_import_wizard_id.with_context(
                    **{**self.context, **self.env.context}
                )._parse_file(base64.b64decode(self.import_attachment_id.datas))
                if not isinstance(parsing_data, list):  # for backward compatibility
                    parsing_data = [parsing_data]
                import_json_data_dict["parsed_statement_data"] = parsing_data
            self.import_json_data = json.loads(
                json.dumps(import_json_data_dict, default=serialize)
            )
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        _logger.info(
            "Finished parsing bank statement file: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def prepare_single_statement_data(
        self,
        single_statement_data: list,
        account_statement_import_wizard_id: models.TransientModel,
        prepared_statement_data: list,
        context: dict,
    ) -> bool:
        try:
            if not isinstance(single_statement_data, list):
                raise UserError(
                    self.env._(
                        "The parsing of the statement file returned an invalid result."
                    )
                )
            currency_code, account_number, stmts_vals = single_statement_data
            # Check raw data
            if not account_statement_import_wizard_id.with_context(
                **context
            )._check_parsed_data(stmts_vals):
                _logger.info(
                    "The parsing of the statement file (%(bank_statement_name)s) "
                    "returned an invalid structure",
                    {"bank_statement_name": self.name},
                )
                return False
            if not currency_code:
                raise UserError(
                    self.env._("Missing currency code in the bank statement file.")
                )
            currency = account_statement_import_wizard_id.with_context(
                **context
            )._match_currency(currency_code)
            journal = account_statement_import_wizard_id.with_context(
                **context
            )._match_journal(account_number, currency)
            if not journal.default_account_id:
                raise UserError(
                    self.env._(
                        "The Bank Accounting Account is not set on the journal '%s'.",
                        journal.display_name,
                    )
                )
            # Prepare statement data to be used for bank statements creation
            if stmts_vals:
                # Complete values (partner mapping etc.)
                stmts_vals = account_statement_import_wizard_id.with_context(
                    **context
                )._complete_stmts_vals(
                    stmts_vals,
                    journal,
                    account_number,
                )
                prepared_statement_data.append(stmts_vals)
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        return True

    def prepare_statement_data(self) -> None:
        try:
            _logger.info(
                "Preparing statement data for import from bank statement file: "
                "%(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = self.import_json_data
            parsing_data = import_json_data_dict["parsed_statement_data"]
            prepared_statement_data = import_json_data_dict[
                "prepared_statement_data_for_import"
            ]
            _logger.info(
                "Bank statement file %s contains %d accounts",
                self.import_attachment_id.name,
                len(parsing_data),
            )
            if parsing_data:
                account_statement_import_wizard_id = self.env[
                    "account.statement.import"
                ].create(
                    {
                        "journal_id": self.journal_id.id,
                        "sheet_mapping_id": self.sheet_mapping_id.id,
                    }
                )
                merged_context = {**self.context, **self.env.context}
                for idx, single_statement_data in enumerate(parsing_data, start=1):
                    _logger.debug(
                        "account %d: single_statement_data=%s",
                        idx,
                        single_statement_data,
                    )
                    self.prepare_single_statement_data(
                        single_statement_data,
                        account_statement_import_wizard_id,
                        prepared_statement_data,
                        merged_context,
                    )
            self.import_json_data = import_json_data_dict
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        _logger.info(
            "Finished preparing statement data for import from bank statement file: "
            "%(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def _create_bank_statements(self, stmts_vals: list, result: dict) -> bool:
        """Create new bank statements from imported values,
        filtering out already imported transactions,
        and return data used by the reconciliation widget"""
        abs_obj = self.env["account.bank.statement"]
        absl_obj = self.env["account.bank.statement.line"]

        # Collect all unique_import_ids to check for existence in batch
        all_unique_import_ids = set()
        for st_vals in stmts_vals:
            for lvals in st_vals.get("transactions", []):
                if lvals.get("unique_import_id"):
                    all_unique_import_ids.add(lvals["unique_import_id"])

        # Batch search for existing lines
        existing_unique_ids = set()
        if all_unique_import_ids:
            existing_lines = absl_obj.sudo().search(
                [("unique_import_id", "in", list(all_unique_import_ids))]
            )
            existing_unique_ids = set(existing_lines.mapped("unique_import_id"))

        # Filter out already imported transactions and create statements
        vals_list = []
        st_lines_list = []
        num_ignored = 0

        for st_vals in stmts_vals:
            st_lines_to_create = []
            for lvals in st_vals.get("transactions", []):
                unique_id = lvals.get("unique_import_id")
                if unique_id and unique_id in existing_unique_ids:
                    num_ignored += 1
                    if "balance_start" in st_vals:
                        st_vals["balance_start"] += float(lvals["amount"])
                else:
                    st_lines_to_create.append(lvals)

            if st_lines_to_create:
                if not st_lines_to_create[0].get("sequence"):
                    for seq, vals in enumerate(st_lines_to_create, start=1):
                        vals["sequence"] = seq

                # Pop data to keep st_vals clean for creation
                st_vals.pop("transactions", None)
                context = st_vals.pop("creation_context", {})

                # Append to batch lists
                vals_list.append(st_vals)
                st_lines_list.append((st_lines_to_create, context))

        if not vals_list:
            return False

        # Create statements in batch
        statements = abs_obj.create(vals_list)

        # Post-creation processing: assign lines and populate result
        for statement, (st_lines_to_create, context) in zip(
            statements, st_lines_list, strict=False
        ):
            for line in st_lines_to_create:
                line["statement_id"] = statement.id

            result["statement_creation_data"][statement.id] = {
                "context": context,
                "statement_line_vals_list": st_lines_to_create,
            }

        result["statement_ids"].extend(statements.ids)

        # Prepare import feedback
        if num_ignored > 0:
            msg = (
                self.env._(  # pylint: disable=translation-not-lazy
                    "%(count)s transaction%(plural)s had already been imported "
                    "and were ignored."
                )
                % {
                    "count": num_ignored,
                    "plural": "s" if num_ignored > 1 else "",
                }
            )
            result["notifications"].append(msg)

        return True

    def create_bank_statements(self) -> None:
        try:
            _logger.info(
                "Creating bank statements: %(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = self.import_json_data
            result = {
                "statement_ids": [],
                "notifications": [],  # list of text messages
                "statement_creation_data": {},
            }
            merged_context = {**self.context, **self.env.context}
            for statement_data in self.import_json_data[
                "prepared_statement_data_for_import"
            ]:
                self.with_context(**merged_context)._create_bank_statements(
                    statement_data, result
                )
            if not result["statement_ids"]:
                raise ImportBankStatementDataError(
                    self.env._(
                        "You have already imported this file, or this file "
                        "only contains already imported transactions."
                    )
                )
            import_json_data_dict.update(result)
            self.import_json_data = import_json_data_dict
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        _logger.info(
            "Finished creating bank statements: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def _create_bank_statement_line(self, vals_list: list, context: dict) -> None:
        try:
            (
                self.env["account.bank.statement.line"]
                .with_context(
                    **context,
                    tracking_disable=True,
                    mail_create_nosubscribe=True,
                    mail_auto_subscribe_no_notify=True,
                    skip_auto_reconcile=True,
                )
                .create(vals_list)
            )
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise

    def create_bank_statement_lines(self) -> Any:
        try:
            _logger.info(
                "Creating bank statement lines: %(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = self.import_json_data
            batch_size = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(
                    "import.bank.statement.line.batch.limit",
                    100,
                )
            )
            jobs = []
            for _, statement_data in import_json_data_dict.get(
                "statement_creation_data", {}
            ).items():
                ctx = statement_data.get("context", {})
                for line_batch in split_every(
                    batch_size, statement_data.get("statement_line_vals_list", [])
                ):
                    jobs.append(
                        self.delayable(
                            description=f"Create Bank Statement Lines: {self.name}",
                            max_retries=1,
                        )._create_bank_statement_line(line_batch, ctx)
                    )

            _logger.info(
                "Create bank statement lines jobs created successfully: %(bs_name)s",
                {"bs_name": self.name},
            )
            return jobs
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise

    def update_balances(self) -> None:
        """Update start and end balances of created bank statements."""
        try:
            _logger.info(
                "Updating bank statement balances: %(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = self.import_json_data
            statement_ids = import_json_data_dict.get("statement_ids", [])
            if statement_ids:
                statement_recs = self.env["account.bank.statement"].browse(
                    statement_ids
                )
                statement_recs._compute_balance_start()
                statement_recs._compute_balance_end()
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        _logger.info(
            "Successfully updated bank statement balances: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def _create_bank_statement_lines_and_update(self) -> None:
        """Create lines and then update result/state."""
        jobs_create_bank_statement_lines = self.create_bank_statement_lines()

        job_update_balances = self.delayable(
            description=f"Update Balances - {self.name}",
            max_retries=1,
        ).update_balances()

        job_update_result = self.delayable(
            description=f"Update Result - {self.name}",
            max_retries=1,
        ).update_result()

        job_update_state_done = self.delayable(
            description=f"Update State - {self.name}",
            max_retries=1,
        ).update_state("done")

        chain(
            *jobs_create_bank_statement_lines,
            job_update_balances,
            job_update_result,
            job_update_state_done,
        ).delay()
        queue_job_recs = self._get_queue_job_recs(job_update_result)
        if queue_job_recs:
            self.queue_job_ids = [(4, job.id) for job in queue_job_recs]

    def update_result(self) -> None:
        try:
            _logger.info(
                "Updating result: %(bank_statement_name)s",
                {"bank_statement_name": self.name},
            )
            import_json_data_dict = self.import_json_data
            statement_ids = import_json_data_dict.get("statement_ids", [])
            self.result = str(
                {
                    "ids": statement_ids,
                    "notifications": import_json_data_dict.get("notifications", []),
                }
            )
            self.res_ids = ",".join(map(str, statement_ids))
        except (ImportBankStatementDataError, Exception) as orig_exception:
            self._handle_import_error(orig_exception)
            raise
        _logger.info(
            "Result updated successfully: %(bank_statement_name)s",
            {"bank_statement_name": self.name},
        )

    def button_import_data(self) -> None:
        """Import prepared data into Odoo."""
        if self.state != "draft":
            raise ValidationError(
                self.env._("Record must be in 'Draft' state for importing data...!")
            )

        # Update state before queueing
        self.update_state("importing_data")

        # Create job chain for import
        ctx = dict(self.env.context)
        if self.journal_id:
            ctx["journal_id"] = self.journal_id.id

        job_parse_data = (
            self.with_context(**ctx)
            .delayable(
                description=f"Parse Bank Statement Data - {self.name}",
                max_retries=1,
            )
            .parse_statement_data()
        )
        job_prepare_statement_data = (
            self.with_context(**ctx)
            .delayable(
                description=f"Prepare Bank Statement Data For Import - {self.name}",
                max_retries=1,
            )
            .prepare_statement_data()
        )
        job_create_bank_statement = (
            self.with_context(**ctx)
            .delayable(
                description=f"Create Bank Statement - {self.name}",
                max_retries=1,
            )
            .create_bank_statements()
        )
        job_create_bank_statement_lines_and_update = (
            self.with_context(**ctx)
            .delayable(
                description=f"Create Bank Statement Lines & Update - {self.name}",
                max_retries=1,
            )
            ._create_bank_statement_lines_and_update()
        )

        chain(
            job_parse_data,
            job_prepare_statement_data,
            job_create_bank_statement,
            job_create_bank_statement_lines_and_update,
        ).delay()
        queue_job_recs = self._get_queue_job_recs(job_parse_data)
        if queue_job_recs:
            self.queue_job_ids = [(6, 0, queue_job_recs.ids)]

    def button_cancel(self) -> None:
        """Cancel import process and related queue jobs."""
        valid_states = [
            "draft",
            "import_data_error",
        ]
        if self.state not in valid_states:
            selection = dict(self._fields["state"].selection)
            valid_state_names = "\n".join(
                selection[k] for k in valid_states if k in selection
            )
            raise ValidationError(
                self.env._(
                    "Record must be in one of the following states "
                    "for cancellation:\n%s",
                    valid_state_names,
                )
            )

        # Cancel related queue jobs efficiently using search instead of filtered
        # Check if there are any jobs first to avoid empty domain query if desired,
        # but search with ID in [] is safe/fast.
        job_ids = self.queue_job_ids.ids
        if job_ids:
            cancelable_jobs = (
                self.env["queue.job"]
                .sudo()
                .search(
                    [
                        ("id", "in", job_ids),
                        ("state", "in", ("pending", "enqueued", "failed")),
                    ]
                )
            )
            if cancelable_jobs:
                cancelable_jobs.button_cancelled()

        self.update_state("cancel")

    def button_draft(self) -> None:
        """Reset record to draft state."""
        self.update_state("draft")
        self.import_json_data = {
            "parsed_statement_data": [],
            "prepared_statement_data_for_import": [],
        }

    def button_open_related_records(self) -> dict:
        """Open related record form view."""
        self.ensure_one()
        action_vals = {
            "name": self.env[self.res_model]._description,
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "context": {"create": False, "edit": False},
            "view_mode": "list,form",
        }
        res_ids = []
        if self.res_ids:
            res_ids += list(map(int, self.res_ids.split(",")))
        if len(res_ids) == 1:
            action_vals.update(
                {
                    "view_mode": "form",
                    "res_id": res_ids[0],
                }
            )
        else:
            action_vals.update(
                {
                    "domain": [("id", "in", res_ids)],
                }
            )
        return action_vals

    def button_open_linked_queue_jobs(self) -> dict:
        """Open linked queue jobs view."""
        self.ensure_one()
        action_vals = {
            "name": self.env._("Queue Jobs"),
            "type": "ir.actions.act_window",
            "res_model": "queue.job",
            "view_mode": "list,form",
        }

        queue_job_ids = self.queue_job_ids.sudo().ids
        if queue_job_ids:
            if len(queue_job_ids) == 1:
                action_vals.update({"view_mode": "form", "res_id": queue_job_ids[0]})
            else:
                action_vals["domain"] = [("id", "in", queue_job_ids)]

        return action_vals

    @api.ondelete(at_uninstall=False)
    def _is_record_deletable(self) -> None:
        """Prevent deletion of non-draft records."""
        non_deletable_recs = self.filtered(lambda r: r.state != "draft")
        if non_deletable_recs:
            error_lines = [f"{rec.name} (ID - {rec.id})" for rec in non_deletable_recs]
            raise ValidationError(
                self.env._(
                    "Can't delete following records as they are not in "
                    "'draft' state:\n%s",
                    "\n".join(error_lines),
                )
            )
