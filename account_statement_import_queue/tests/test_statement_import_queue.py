# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_statement_import_queue.exception import (
    ImportBankStatementDataError,
)


@tagged("post_install", "-at_install")
class TestAccountStatementImportQueue(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.queue_job import delay

        delay._logger.warning = lambda *args, **kwargs: None
        cls.company = cls.company_data["company"]
        cls.journal = cls.company_data["default_journal_bank"]
        cls.attachment = cls.env["ir.attachment"].create(
            {
                "name": "test_statement.csv",
                "type": "binary",
                "datas": base64.b64encode(
                    b"date,amount,name\n2026-03-23,100,Test Payment"
                ),
                "res_model": "import.bank.statement.history",
            }
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def test_01_batch_import_wizard(self):
        """Test the batch import wizard creation of history record."""
        wizard = (
            self.env["account.statement.import"]
            .with_context(
                active_model="account.journal",
                active_id=self.journal.id,
                journal_id=self.journal.id,
            )
            .create(
                {
                    "statement_file": self.attachment.datas,
                    "statement_filename": "test_statement.csv",
                }
            )
        )
        action = wizard.action_import_batch()
        self.assertEqual(action["res_model"], "import.bank.statement.history")
        history = self.env["import.bank.statement.history"].browse(action["res_id"])
        self.assertTrue(history.exists())
        self.assertEqual(history.name, "test_statement.csv")
        self.assertEqual(history.state, "draft")
        history.button_import_data()
        self.assertEqual(history.state, "importing_data")

    def test_02_history_state_transitions(self):
        """Test manual state transitions (Draft/Cancel)."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "manual_test.csv",
                "journal_id": self.journal.id,
            }
        )
        self.assertEqual(history.state, "draft")
        history.button_cancel()
        self.assertEqual(history.state, "cancel")
        history.button_draft()
        self.assertEqual(history.state, "draft")

    def test_03_unlink_protection(self):
        """Test that history records cannot be deleted in 'importing_data' state."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "unlink_test.csv",
                "journal_id": self.journal.id,
                "state": "importing_data",
            }
        )
        with self.assertRaises(ValidationError):
            history.unlink()
        history.state = "draft"
        history.unlink()
        self.assertFalse(history.exists())

    def test_04_button_draft(self):
        """Test resetting history record to draft."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "draft_test.csv",
                "journal_id": self.journal.id,
                "state": "import_data_error",
                "import_json_data": {"test": "data"},
            }
        )
        history.button_draft()
        self.assertEqual(history.state, "draft")
        self.assertEqual(history.import_json_data.get("parsed_statement_data"), [])

    def test_05_cleanup(self):
        """Test cleanup of empty bank statements."""
        statement = self.env["account.bank.statement"].create(
            {
                "name": "test_statement_cleanup",
                "journal_id": self.journal.id,
            }
        )
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "cleanup_test.csv",
                "journal_id": self.journal.id,
                "import_json_data": {"statement_ids": [statement.id]},
            }
        )
        history._perform_cleanup()
        self.assertFalse(statement.exists())
        self.assertEqual(history.import_json_data.get("statement_ids"), [])

    def test_06_button_actions(self):
        """Test UI action buttons."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "action_test.csv",
                "journal_id": self.journal.id,
                "res_model": "account.bank.statement",
                "res_ids": "1,2,3",
            }
        )
        action = history.button_open_related_records()
        self.assertEqual(action["res_model"], "account.bank.statement")
        self.assertEqual(action["domain"], [("id", "in", [1, 2, 3])])
        action = history.button_open_linked_queue_jobs()
        self.assertEqual(action["res_model"], "queue.job")
        self.assertTrue("view_mode" in action)

    def test_07_full_import_lifecycle(self):
        """Test the full import lifecycle by calling methods directly."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "lifecycle_test.csv",
                "journal_id": self.journal.id,
                "import_attachment_id": self.attachment.id,
            }
        )

        parsed_statement = [
            "USD",
            self.journal.bank_account_id.acc_number or "123",
            [
                {
                    "name": "Statement 1",
                    "balance_start": 0.0,
                    "balance_end_real": 100.0,
                    "transactions": [
                        {
                            "date": "2026-03-23",
                            "payment_ref": "Line 1",
                            "name": "Line 1",
                            "amount": 100,
                            "unique_import_id": "L1",
                        }
                    ],
                }
            ],
        ]

        mock_cr_cm = MagicMock()
        mock_cr_cm.__enter__.return_value = self.env.cr

        with (
            patch(
                "odoo.addons.account_statement_import_sheet_file.models.account_statement_import.AccountStatementImport._parse_file",
                return_value=[parsed_statement],
            ),
            patch(
                "odoo.addons.account_statement_import_file.wizard.account_statement_import.AccountStatementImport._match_journal",
                return_value=self.journal,
            ),
            patch.object(self.env.cr, "rollback", side_effect=lambda: None),
            patch("odoo.modules.registry.Registry.cursor", return_value=mock_cr_cm),
        ):
            # 1. Parse
            history.parse_statement_data()
            self.assertTrue(history.import_json_data.get("parsed_statement_data"))

            # 2. Prepare
            history.prepare_statement_data()
            self.assertTrue(
                history.import_json_data.get("prepared_statement_data_for_import")
            )

            # 3. Create Statements
            history.create_bank_statements()
            self.assertTrue(history.import_json_data.get("statement_ids"))

            # 4. Create Lines
            statement_data = history.import_json_data["statement_creation_data"]
            for _st_id, data in statement_data.items():
                history._create_bank_statement_line(
                    data["statement_line_vals_list"], data["context"]
                )

            # 5. Update Balances & Result
            history.update_balances()
            history.update_result()
            history.update_state("done")

        self.assertEqual(history.state, "done")

    def test_08_duplicate_detection(self):
        """Test detection and skipping of duplicated transactions."""
        self.env["account.bank.statement.line"].create(
            {
                "date": "2026-03-23",
                "name": "Duplicate",
                "amount": 100,
                "journal_id": self.journal.id,
                "unique_import_id": "UNIQUE_123",
            }
        )

        stmts_vals = [
            {
                "name": "Test Statement",
                "journal_id": self.journal.id,
                "transactions": [
                    {
                        "date": "2026-03-23",
                        "name": "Duplicate",
                        "amount": 100,
                        "unique_import_id": "UNIQUE_123",
                    },
                    {
                        "date": "2026-03-23",
                        "name": "New",
                        "amount": 200,
                        "unique_import_id": "UNIQUE_456",
                    },
                ],
            }
        ]

        history = self.env["import.bank.statement.history"].create(
            {
                "name": "duplicate_test.csv",
                "journal_id": self.journal.id,
            }
        )

        result = {
            "statement_ids": [],
            "notifications": [],
            "statement_creation_data": {},
        }
        history._create_bank_statements(stmts_vals, result)

        self.assertEqual(len(result["statement_ids"]), 1)
        self.assertTrue(
            any("already been imported" in n for n in result["notifications"])
        )

    def test_09_import_error_handling(self):
        """Test error handling when an exception occurs during import."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "error_test.csv",
                "journal_id": self.journal.id,
            }
        )

        mock_cr_cm = MagicMock()
        mock_cr_cm.__enter__.return_value = self.env.cr

        with (
            patch.object(self.env.cr, "rollback", side_effect=lambda: None),
            patch("odoo.modules.registry.Registry.cursor", return_value=mock_cr_cm),
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history._logger"
            ) as mock_logger,
        ):
            try:
                raise ValueError("Test Error")
            except ValueError as e:
                history._handle_import_error(e)

        self.assertEqual(history.state, "import_data_error")
        self.assertEqual(history.exc_message, "Test Error")
        mock_logger.error.assert_called()

    def test_10_additional_ui_and_state_checks(self):
        """Test remaining UI actions and state validation errors."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "ui_test.csv",
                "journal_id": self.journal.id,
                "res_model": "account.bank.statement",
                "res_ids": "1",
                "state": "done",
            }
        )
        action = history.button_open_related_records()
        self.assertEqual(action["res_id"], 1)

        with self.assertRaises(ValidationError):
            history.button_cancel()

        action = history.button_open_linked_queue_jobs()
        self.assertEqual(action["res_model"], "queue.job")

        history.import_json_data = {
            "statement_creation_data": {
                "1": {"context": {}, "statement_line_vals_list": [{"name": "L1"}]}
            }
        }
        jobs = history.create_bank_statement_lines()
        self.assertEqual(len(jobs), 1)

    def test_11_missing_configuration_errors(self):
        """Test errors due to missing configuration."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "config_error_test.csv",
                "journal_id": self.journal.id,
            }
        )

        self.assertFalse(
            history._create_bank_statements(
                [{"name": "Missing Trans"}],
                {
                    "statement_ids": [],
                    "notifications": [],
                    "statement_creation_data": {},
                },
            )
        )

        self.journal.default_account_id = False
        parsed_statement = [
            "USD",
            "123",
            [
                {
                    "name": "S1",
                    "transactions": [
                        {
                            "name": "L1",
                            "payment_ref": "L1",
                            "amount": 100,
                            "date": "2026-03-23",
                        }
                    ],
                }
            ],
        ]
        wizard = self.env["account.statement.import"].create(
            {"journal_id": self.journal.id}
        )

        mock_cr_cm = MagicMock()
        mock_cr_cm.__enter__.return_value = self.env.cr

        with (
            patch(
                "odoo.addons.account_statement_import_file.wizard.account_statement_import.AccountStatementImport._match_journal",
                return_value=self.journal,
            ),
            patch.object(self.env.cr, "rollback", side_effect=lambda: None),
            patch("odoo.modules.registry.Registry.cursor", return_value=mock_cr_cm),
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history._logger"
            ),
        ):
            with self.assertRaises(UserError):
                history.prepare_single_statement_data(parsed_statement, wizard, [], {})

    def test_12_wizard_standard_import(self):
        """Test the standard _import_file method in the wizard."""
        wizard = (
            self.env["account.statement.import"]
            .with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            )
            .create(
                {
                    "statement_file": self.attachment.datas,
                    "statement_filename": "test.csv",
                }
            )
        )
        # Correct path for OCA Odoo 18
        with patch(
            "odoo.addons.account_statement_import_file.wizard.account_statement_import.AccountStatementImport._import_file",
            return_value=True,
        ):
            self.assertTrue(wizard._import_file())

        wizard.statement_file = False
        with self.assertRaises(ValidationError):
            wizard._import_file()

    def test_13_wizard_validation(self):
        """Test action_import_batch validation."""
        wizard = self.env["account.statement.import"].create({})
        with self.assertRaises(ValidationError):
            wizard.action_import_batch()

    def test_14_async_job_chain(self):
        """Test direct call to _create_bank_statement_lines_and_update
        and its job chain."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "chain_test.csv",
                "journal_id": self.journal.id,
                "import_json_data": {
                    "statement_creation_data": {
                        "1": {
                            "context": {},
                            "statement_line_vals_list": [{"name": "L1"}],
                        }
                    }
                },
            }
        )
        # Mock chain and with_delay to avoid read-only issues and warnings
        with (
            patch(
                "odoo.addons.queue_job.models.base.Base.with_delay",
                return_value=MagicMock(),
            ),
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history.ImportBankStatementHistory._get_queue_job_recs"
            ) as mock_get_recs,
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history.chain"
            ) as mock_chain,
        ):
            mock_get_recs.return_value = self.env["queue.job"]
            history._create_bank_statement_lines_and_update()
            mock_chain.assert_called()

    def test_15_manual_action_validations(self):
        """Test validation errors for manual button actions in wrong states."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "state_test.csv",
                "journal_id": self.journal.id,
                "state": "importing_data",
            }
        )
        with self.assertRaises(ValidationError):
            history.button_import_data()

        history.state = "draft"
        history.button_cancel()
        self.assertEqual(history.state, "cancel")

        history.state = "done"
        with self.assertRaises(ValidationError):
            history.button_cancel()

    def test_16_complex_data_recovery(self):
        """Test edge cases in prepare_single_statement_data and balance updates."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "complex_test.csv",
                "journal_id": self.journal.id,
            }
        )
        wizard = (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create(
                {
                    "journal_id": self.journal.id,
                }
            )
        )

        mock_cr_cm = MagicMock()
        mock_cr_cm.__enter__.return_value = self.env.cr

        with (
            patch.object(self.env.cr, "rollback", side_effect=lambda: None),
            patch("odoo.modules.registry.Registry.cursor", return_value=mock_cr_cm),
            patch(
                "odoo.addons.account_statement_import_file.wizard.account_statement_import.AccountStatementImport._check_parsed_data",
                return_value=True,
            ),
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history._logger"
            ),
        ):
            with self.assertRaises(UserError) as cm:
                history.prepare_single_statement_data(
                    {"invalid": "dict"}, wizard, [], {}
                )
            self.assertIn("invalid result", cm.exception.args[0])

            with self.assertRaises(UserError) as cm:
                history.prepare_single_statement_data(["", "123", []], wizard, [], {})
            self.assertIn("Missing currency code", cm.exception.args[0])

        self.env["account.bank.statement.line"].create(
            {
                "date": "2026-03-23",
                "name": "D",
                "amount": 100,
                "journal_id": self.journal.id,
                "unique_import_id": "D1",
            }
        )
        stmts_vals = [
            {
                "name": "S1",
                "balance_start": 0.0,
                "transactions": [
                    {"unique_import_id": "D1", "amount": 100, "date": "2026-03-23"}
                ],
            }
        ]
        history._create_bank_statements(
            stmts_vals,
            {"statement_ids": [], "notifications": [], "statement_creation_data": {}},
        )
        self.assertEqual(stmts_vals[0]["balance_start"], 100.0)

    def test_17_job_ui_and_cancel_logic(self):
        """Test UI for multiple jobs and button_cancel with actual jobs."""
        history = self.env["import.bank.statement.history"].create(
            {
                "name": "job_ui_test.csv",
                "journal_id": self.journal.id,
            }
        )
        job_sentinel = self.env["queue.job"].EDIT_SENTINEL
        job1 = (
            self.env["queue.job"]
            .sudo()
            .with_context(_job_edit_sentinel=job_sentinel)
            .create(
                {
                    "name": "Job 1",
                    "state": "pending",
                    "method_name": "write",
                    "model_name": "res.users",
                    "uuid": "uuid1",
                }
            )
        )
        job2 = (
            self.env["queue.job"]
            .sudo()
            .with_context(_job_edit_sentinel=job_sentinel)
            .create(
                {
                    "name": "Job 2",
                    "state": "pending",
                    "method_name": "write",
                    "model_name": "res.users",
                    "uuid": "uuid2",
                }
            )
        )
        history.queue_job_ids = [(6, 0, [job1.id, job2.id])]

        action = history.button_open_linked_queue_jobs()
        self.assertEqual(action.get("domain"), [("id", "in", [job1.id, job2.id])])

        # Mock Job.load to bypass method resolution
        with patch("odoo.addons.queue_job.job.Job.load") as mock_load:
            mock_job = MagicMock()
            mock_load.return_value = mock_job
            history.button_cancel()
            self.assertEqual(mock_load.call_count, 2)

        mock_cr_cm = MagicMock()
        mock_cr_cm.__enter__.return_value = self.env.cr
        with (
            patch(
                "odoo.addons.queue_job.models.base.Base.with_delay",
                return_value=MagicMock(),
            ),
            patch.object(self.env.cr, "rollback", side_effect=lambda: None),
            patch("odoo.modules.registry.Registry.cursor", return_value=mock_cr_cm),
            patch(
                "odoo.addons.account_statement_import_queue.models.import_bank_statement_history._logger"
            ),
        ):
            history.import_json_data = {"prepared_statement_data_for_import": [[]]}
            with self.assertRaises(ImportBankStatementDataError):
                history.create_bank_statements()
