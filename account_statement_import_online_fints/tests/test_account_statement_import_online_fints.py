# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from fints.exceptions import FinTSSCARequiredError
from fints.utils import mt940_to_array
from freezegun import freeze_time

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common
from odoo.tools import file_open, mute_logger

_module = "odoo.addons.account_statement_import_online_fints"
_provider_module = _module + ".models.online_bank_statement_provider"
_wizard_module = _module + ".wizards.online_bank_statement_fints_tan"

IBAN = "DE89370400440532013000"


class FakeTANResponse:
    """Replaces fints.client.NeedTANResponse, which needs real bank segments"""

    def __init__(self, decoupled=False, name="init"):
        self.decoupled = decoupled
        self.name = name
        self.resume_method = "resume"
        self.challenge_html = "Confirm the access"
        self.challenge_matrix = None
        self.challenge_hhduc = None

    def get_data(self):
        return f"{self.name}:{self.resume_method}".encode()

    @classmethod
    def from_data(cls, blob):
        name, resume_method = blob.decode().split(":")
        response = cls(name=name)
        response.resume_method = resume_method
        return response


class FakeClient:
    """Replaces fints.client.FinTS3PinTanClient, simulating a bank which
    needs `confirmations` decoupled confirmations on the dialog init"""

    bank = None
    tan_segment_types = frozenset()

    def __init__(self, *args, **kwargs):
        self.from_data = kwargs.get("from_data")
        self.selected_tan_medium = None
        # The selected TAN method is restored from the stored client data
        self.selected_security_function = "940" if self.from_data else None
        self.init_tan_response = None
        self.bpd = SimpleNamespace(
            find_segment_first=lambda name: name == "HIKAZS" and self.bank.mt940
        )

    def fetch_tan_mechanisms(self):
        self.selected_security_function = self.bank.auto_mechanism
        return self.selected_security_function

    def get_tan_mechanisms(self):
        return {
            "940": SimpleNamespace(
                name="SecurePlus",
                wait_before_first_poll=5,
                wait_before_next_poll=2,
                decoupled_max_poll_number=self.bank.max_polls,
            )
        }

    def get_current_tan_mechanism(self):
        return self.selected_security_function

    def set_tan_mechanism(self, code):
        self.selected_security_function = code

    def is_tan_media_required(self):
        return False

    def __enter__(self):
        self.bank.mechanism = self.selected_security_function
        if self.bank.confirmations:
            self.init_tan_response = FakeTANResponse(decoupled=True)

    def __exit__(self, *args):
        pass

    def get_sepa_accounts(self):
        return [SimpleNamespace(iban=iban) for iban in self.bank.ibans]

    def get_transactions(self, account, start_date, end_date):
        assert self.bank.mt940
        self.last_fetch = ("get_transactions", (account, start_date, end_date))
        self.bank.fetched.append((account.iban, start_date, end_date))
        if self.bank.sca_required:
            raise FinTSSCARequiredError("Starke Authentifizierung erforderlich.")
        if self.bank.transactions_tan:
            return FakeTANResponse(decoupled=True, name="transactions")
        with file_open(
            "account_statement_import_online_fints/tests/samples/mt940.sta"
        ) as f:
            return mt940_to_array(f.read())

    def get_transactions_xml(self, account, start_date, end_date):
        assert not self.bank.mt940
        self.last_fetch = ("get_transactions_xml", (account, start_date, end_date))
        self.bank.fetched.append((account.iban, start_date, end_date))
        if self.bank.transactions_tan:
            return FakeTANResponse(decoupled=True, name="transactions")
        with file_open(
            "account_statement_import_online_fints/tests/samples/camt052.xml", "rb"
        ) as f:
            return [f.read()], []

    def pause_dialog(self):
        return b"dialog"

    @contextmanager
    def resume_dialog(self, dialog_data):
        assert dialog_data == b"dialog"
        yield self

    def send_tan(self, challenge, tan):
        assert challenge.decoupled
        self.bank.polls += 1
        if challenge.name == "transactions":
            self.bank.transactions_tan = False
            if challenge.resume_method == "_continue_check_transactions_access":
                return None
            method, args = self.last_fetch
            return getattr(self, method)(*args)
        self.bank.confirmations -= 1
        if self.bank.confirmations:
            return FakeTANResponse(decoupled=True)
        return SimpleNamespace(name="init response")

    def deconstruct(self, including_private=False):
        return b"client data"


class TestAccountStatementImportOnlineFints(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "FinTS Bank",
                "type": "bank",
                "code": "FINTS",
                "bank_statements_source": "online",
                "bank_acc_number": IBAN,
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "fints",
                "journal_id": cls.journal.id,
                "statement_creation_mode": "daily",
                "tz": "Europe/Berlin",
                "fints_blz": "37040044",
                "api_base": "https://fints.example.com/",
                "username": "user",
                "password": "pin",
                "fints_product_id": "PRODUCT",
            }
        )

    def setUp(self):
        super().setUp()
        self.bank = SimpleNamespace(
            confirmations=0,
            ibans=[IBAN],
            fetched=[],
            transactions_tan=False,
            sca_required=False,
            mt940=True,
            polls=0,
            max_polls=3,
            auto_mechanism="940",
            mechanism=None,
        )
        FakeClient.bank = self.bank
        self.sleep = mock.Mock()
        for patcher in (
            mock.patch(_provider_module + ".sleep", self.sleep),
            mock.patch(_provider_module + ".FinTS3PinTanClient", FakeClient),
            mock.patch(_provider_module + ".NeedTANResponse", FakeTANResponse),
            mock.patch(_wizard_module + ".NeedTANResponse", FakeTANResponse),
            mock.patch(_wizard_module + ".NeedRetryResponse", FakeTANResponse),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _pull(self, scheduled=False):
        self.provider.with_context(scheduled=scheduled)._pull(
            datetime(2026, 10, 1, 8), datetime(2026, 10, 2, 8)
        )

    def _assert_balances(self, statement, balance_start, balance_end_real):
        self.assertEqual(len(statement), 1)
        self.assertAlmostEqual(statement.balance_start, balance_start)
        self.assertAlmostEqual(statement.balance_end_real, balance_end_real)
        self.assertTrue(statement.is_complete)

    def _mt940_sample(self):
        with file_open(
            "account_statement_import_online_fints/tests/samples/mt940.sta"
        ) as f:
            return f.read()

    def _statement_lines(self):
        return self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id)]
        )

    @freeze_time("2026-10-01 23:00:00")
    def test_connect(self):
        admin = self.env.ref("base.user_admin")
        action = self.provider.with_user(admin).action_fints_connect()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(self.provider.fints_state, "connected")
        self.assertEqual(self.provider.fints_tan_mechanisms, "940: SecurePlus")
        # The user gets informed when the bank asks for a confirmation again
        self.assertIn(admin.partner_id, self.provider.message_partner_ids)
        # The access to the transactions is checked, for today of the provider
        self.assertEqual(
            self.bank.fetched,
            [(IBAN, datetime(2026, 10, 2).date(), datetime(2026, 10, 2).date())],
        )

    def test_connect_confirm_transactions_access(self):
        """Some banks only ask for the confirmation when fetching the
        transactions, the connection asks for it"""
        self.bank.transactions_tan = True
        action = self.provider.action_fints_connect()
        self.assertEqual(self.provider.fints_state, "tan_required")
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertTrue(wizard.decoupled)
        action = wizard.action_confirm()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(self.provider.fints_state, "connected")
        # Checked again after the confirmation
        self.assertEqual(len(self.bank.fetched), 2)

    def test_connect_confirm_transactions_access_camt(self):
        self.bank.mt940 = False
        self.bank.transactions_tan = True
        action = self.provider.action_fints_connect()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        wizard.action_confirm()
        self.assertEqual(self.provider.fints_state, "connected")

    def test_journal_generate_unique_import_id(self):
        """FinTS journals always generate the missing import ids"""
        self.assertTrue(self.journal.generate_unique_import_id)
        with self.assertRaisesRegex(ValidationError, "must stay enabled"):
            self.journal.generate_unique_import_id = False

    def test_connect_one_step_mechanism(self):
        """python-fints keeps the one step method if the bank allows it"""
        self.bank.auto_mechanism = "999"
        self.provider.action_fints_connect()
        self.assertEqual(self.bank.mechanism, "940")
        self.assertEqual(self.provider.fints_state, "connected")

    def test_connect_decoupled(self):
        self.bank.confirmations = 2
        action = self.provider.action_fints_connect()
        self.assertEqual(self.provider.fints_state, "tan_required")
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertTrue(wizard.decoupled)
        self.assertFalse(wizard.pending)
        # The first confirmation is not done in the app yet
        action = wizard.action_confirm()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertTrue(wizard.pending)
        action = wizard.action_confirm()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(self.provider.fints_state, "connected")

    def test_connect_forged_dialog_data(self):
        """The paused dialog is restored with pickle, data written by a user
        is refused before it is restored"""
        from base64 import b64encode

        self.bank.confirmations = 2
        action = self.provider.action_fints_connect()
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        resume_dialog = mock.Mock()
        with mock.patch.object(FakeClient, "resume_dialog", resume_dialog):
            for vals in (
                {"dialog_data": b64encode(b"forged")},
                {"tan_data": b64encode(b"forged")},
                {"signature": "forged"},
            ):
                forged = wizard.copy(vals)
                with self.assertRaisesRegex(UserError, "invalid"):
                    forged.action_confirm()
            forged = self.env[action["res_model"]].create(
                {
                    "provider_id": self.provider.id,
                    "dialog_data": b64encode(b"forged"),
                    "tan_data": b64encode(b"init:resume"),
                }
            )
            with self.assertRaisesRegex(UserError, "invalid"):
                forged.action_confirm()
        resume_dialog.assert_not_called()
        # The data signed by the server is still accepted
        action = wizard.action_confirm()
        self.assertEqual(self.bank.polls, 1)

    def test_connect_unknown_account(self):
        self.bank.ibans = ["DE02120300000000202051"]
        with self.assertRaisesRegex(UserError, "not available"):
            self.provider.action_fints_connect()

    def test_connect_unknown_tan_mechanism(self):
        self.provider.fints_tan_mechanism = "999"
        with self.assertRaisesRegex(UserError, "TAN method 999"):
            self.provider.action_fints_connect()

    def test_pull_not_connected(self):
        with self.assertRaisesRegex(UserError, "not connected"):
            self._pull()

    @freeze_time("2026-10-02 10:00:00")
    def test_pull_mt940(self):
        self.provider.action_fints_connect()
        self._pull()
        lines = self._statement_lines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(sorted(lines.mapped("amount")), [-4.9, -4.9, 100.0])
        self.assertEqual(len(set(lines.mapped("unique_import_id"))), 3)
        self._assert_balances(lines.statement_id, 1000.0, 1090.2)
        customer_line = lines.filtered(lambda line: line.amount == 100)
        self.assertEqual(customer_line.payment_ref, "Invoice INV/2026/0001")
        self.assertEqual(customer_line.ref, "E2E123")
        self.assertEqual(customer_line.partner_name, "Some Customer")
        self.assertEqual(customer_line.account_number, "DE02120300000000202051")
        self.assertIn("Posting Text: SEPA-GUTSCHRIFT", customer_line.narration)
        fee_line = lines.filtered(lambda line: line.amount < 0)[0]
        self.assertEqual(fee_line.payment_ref, "Kontofuehrung")
        self.assertFalse(fee_line.ref)
        # Pulling the same period again does not duplicate the lines
        self._pull()
        self.assertEqual(self._statement_lines(), lines)

    @freeze_time("2026-10-02 10:00:00")
    def test_pull_camt(self):
        self.bank.mt940 = False
        self.provider.action_fints_connect()
        self.bank.fetched.clear()
        self._pull()
        self.assertEqual(
            self.bank.fetched,
            [
                (IBAN, datetime(2026, 10, 1).date(), datetime(2026, 10, 1).date()),
                (IBAN, datetime(2026, 10, 2).date(), datetime(2026, 10, 2).date()),
            ],
        )
        lines = self._statement_lines()
        # The sample is returned for each day, but only fits the first one
        self.assertEqual(len(lines), 3)
        self.assertEqual(sorted(lines.mapped("amount")), [-4.9, -4.9, 100.0])
        self.assertEqual(len(set(lines.mapped("unique_import_id"))), 3)
        self._assert_balances(lines.statement_id, 1000.0, 1090.2)
        customer_line = lines.filtered(lambda line: line.amount == 100)
        self.assertEqual(customer_line.partner_name, "Some Customer")
        self.assertEqual(customer_line.account_number, "DE02120300000000202051")
        # Pulling the same period again does not duplicate the lines
        self._pull()
        self.assertEqual(self._statement_lines(), lines)

    @freeze_time("2026-10-01 10:00:00")
    def test_pull_not_in_future(self):
        self.provider.action_fints_connect()
        self.bank.fetched.clear()
        self._pull()
        self.assertEqual(
            self.bank.fetched,
            [(IBAN, datetime(2026, 10, 1).date(), datetime(2026, 10, 1).date())],
        )

    @freeze_time("2026-10-01 23:00:00")
    def test_pull_today_of_provider(self):
        """Shortly after midnight in Berlin, today is already the 02.10.,
        whatever the timezone of the user running the pull"""
        self.env.user.tz = "UTC"
        self.provider.action_fints_connect()
        self.bank.fetched.clear()
        self._pull()
        self.assertEqual(
            self.bank.fetched,
            [
                (IBAN, datetime(2026, 10, 1).date(), datetime(2026, 10, 1).date()),
                (IBAN, datetime(2026, 10, 2).date(), datetime(2026, 10, 2).date()),
            ],
        )

    @freeze_time("2026-10-02 10:00:00")
    @mute_logger(
        "odoo.addons.account_statement_import_online.models."
        "online_bank_statement_provider"
    )
    def test_pull_confirmation_required(self):
        self.provider.action_fints_connect()
        self.bank.transactions_tan = True
        old_messages = self.provider.message_ids
        self._pull(scheduled=True)
        self.assertEqual(self.provider.fints_state, "tan_required")
        self.assertFalse(self._statement_lines())
        # The followers got informed once
        messages = self.provider.message_ids - old_messages
        self.assertEqual(
            len(messages.filtered(lambda m: "confirm the access again" in m.body)), 1
        )
        with self.assertRaisesRegex(UserError, "not connected"):
            self._pull()

    @freeze_time("2026-10-02 10:00:00")
    @mute_logger(
        "odoo.addons.account_statement_import_online.models."
        "online_bank_statement_provider"
    )
    def test_pull_sca_required(self):
        """Some banks reject a command (9075) to ask for the confirmation"""
        self.provider.action_fints_connect()
        self.bank.sca_required = True
        self._pull(scheduled=True)
        self.assertEqual(self.provider.fints_state, "tan_required")
        self.assertFalse(self._statement_lines())

    def test_end_bootstrap_mode(self):
        """python-fints raises FinTSSCARequiredError only out of its bootstrap
        mode, which it only ends in get_tan_media()"""
        from fints.client import FinTS3PinTanClient as BaseClient

        from ..models.fints_client import FinTS3PinTanClient

        client = FinTS3PinTanClient(
            "12345678", "user", "pin", "https://fints.example.com/", product_id="P"
        )
        self.assertTrue(client._bootstrap_mode)
        with mock.patch.object(BaseClient, "__enter__"):
            client.__enter__()
        self.assertFalse(client._bootstrap_mode)

    @freeze_time("2026-10-02 10:00:00")
    def test_pull_wait_confirmation(self):
        self.provider.action_fints_connect()
        self.provider.fints_confirmation_timeout = 5
        # The bank asks for a confirmation in the app on every login
        self.bank.confirmations = 2
        self.provider._pull(datetime(2026, 10, 1, 8), datetime(2026, 10, 1, 9))
        self.assertEqual(self.bank.polls, 2)
        self.assertEqual(self.sleep.call_args_list, [mock.call(5), mock.call(2)])
        self.assertEqual(len(self._statement_lines()), 3)

    @freeze_time("2026-10-02 10:00:00")
    def test_pull_wait_transactions_confirmation(self):
        """The bank asks for a confirmation in the app to fetch the
        transactions"""
        self.provider.action_fints_connect()
        self.provider.fints_confirmation_timeout = 5
        self.bank.transactions_tan = True
        self.provider._pull(datetime(2026, 10, 1, 8), datetime(2026, 10, 1, 9))
        self.assertEqual(self.bank.polls, 1)
        self.assertEqual(len(self._statement_lines()), 3)
        self.assertEqual(self.provider.fints_state, "connected")

    def _client_send_rejected_without_tan(self, security_function="940", sends=1):
        """Send a command `sends` times with the client to a bank which
        rejects it without a TAN segment (9075), return the client and
        whether each try had one"""
        from fints.client import FinTS3PinTanClient as BaseClient

        from ..models.fints_client import FinTS3PinTanClient

        client = FinTS3PinTanClient(
            "12345678", "user", "pin", "https://fints.example.com/", product_id="P"
        )
        client.selected_security_function = security_function
        command_seg = SimpleNamespace(header=SimpleNamespace(type="HKKAZ"))
        tries = []

        def send(client, dialog, command_seg, resume_func):
            tries.append(client._need_twostep_tan_for_segment(command_seg))
            if not tries[-1] or self.bank.sca_required:
                raise FinTSSCARequiredError("Starke Authentifizierung erforderlich.")
            return "confirmation asked"

        with (
            mock.patch.object(
                BaseClient, "_send_with_possible_retry", autospec=True, side_effect=send
            ),
            mock.patch.object(
                BaseClient, "_need_twostep_tan_for_segment", return_value=False
            ),
        ):
            for __ in range(sends):
                self.assertEqual(
                    client._send_with_possible_retry(None, command_seg, None),
                    "confirmation asked",
                )
        return client, tries

    def test_client_sca_required_retry_with_tan(self):
        """A command rejected without a TAN segment (9075) is sent again with
        one, for the bank to ask for the confirmation, the next ones get one
        right away"""
        client, tries = self._client_send_rejected_without_tan(sends=2)
        self.assertEqual(tries, [False, True, True])
        self.assertEqual(client.tan_segment_types, {"HKKAZ"})

    def test_client_sca_required_with_tan(self):
        """A command rejected with a TAN segment is not sent again"""
        self.bank.sca_required = True
        with self.assertRaises(FinTSSCARequiredError):
            self._client_send_rejected_without_tan()

    def test_client_sca_required_one_step(self):
        """The one step method has no TAN segment to send again"""
        with self.assertRaises(FinTSSCARequiredError):
            self._client_send_rejected_without_tan(security_function="999")

    @freeze_time("2026-10-02 10:00:00")
    def test_client_data_admin_only(self):
        """An accountant connects and pulls, but can neither read the PIN nor
        the client data with the account numbers and names"""
        accountant = self.env["res.users"].create(
            {
                "name": "Accountant",
                "login": "fints_accountant",
                "groups_id": [(6, 0, self.env.ref("account.group_account_user").ids)],
            }
        )
        provider = self.provider.with_user(accountant)
        provider.action_fints_connect()
        provider.with_context(scheduled=False)._pull(
            datetime(2026, 10, 1, 8), datetime(2026, 10, 2, 8)
        )
        self.assertEqual(len(self._statement_lines()), 3)
        provider.invalidate_recordset()
        for field in ("password", "fints_client_data"):
            with self.assertRaises(AccessError):
                provider.read([field])
        self.assertTrue(self.provider.fints_client_data)
        provider.action_fints_disconnect()
        self.assertFalse(self.provider.fints_client_data)

    def test_tan_segment_types_kept(self):
        """The commands the bank only accepts with a TAN segment are kept
        between the pulls, until the provider gets disconnected"""
        self.provider.action_fints_connect()
        self.assertFalse(self.provider.fints_tan_segment_types)
        client = self.provider._fints_get_client()
        self.assertFalse(client.tan_segment_types)
        client.tan_segment_types = frozenset({"HKKAZ", "HKCAZ"})
        self.provider._fints_store_client(client)
        self.assertEqual(self.provider.fints_tan_segment_types, "HKCAZ,HKKAZ")
        client = self.provider._fints_get_client()
        self.assertEqual(client.tan_segment_types, {"HKKAZ", "HKCAZ"})
        self.provider.action_fints_disconnect()
        self.assertFalse(self.provider.fints_tan_segment_types)

    @freeze_time("2026-10-02 10:00:00")
    @mute_logger(
        "odoo.addons.account_statement_import_online.models."
        "online_bank_statement_provider"
    )
    def test_pull_wait_confirmation_timeout(self):
        self.provider.action_fints_connect()
        self.provider.fints_confirmation_timeout = 5
        self.bank.confirmations = 10
        self._pull(scheduled=True)
        # The bank allows 3 polls only
        self.assertEqual(self.bank.polls, 3)
        self.assertFalse(self._statement_lines())
        # The next pull asks for a confirmation again
        self.assertEqual(self.provider.fints_state, "connected")

    @freeze_time("2026-10-02 10:00:00")
    @mute_logger(
        "odoo.addons.account_statement_import_online.models."
        "online_bank_statement_provider"
    )
    def test_pull_wait_confirmation_deadline(self):
        """The pull stops waiting before the configured time is over"""
        self.provider.action_fints_connect()
        self.provider.fints_confirmation_timeout = 1
        self.bank.confirmations = 100
        self.bank.max_polls = None
        clock = [0]

        def sleep(seconds):
            clock[0] += seconds

        self.sleep.side_effect = sleep
        with mock.patch(_provider_module + ".monotonic", lambda: clock[0]):
            self._pull(scheduled=True)
        # Polls after 5 seconds, then every 2 seconds, the last one after 59
        self.assertEqual(clock[0], 59)
        self.assertEqual(self.bank.polls, 28)
        self.assertFalse(self._statement_lines())
        self.assertEqual(self.provider.fints_state, "connected")

    def test_split_iban(self):
        split = self.env["online.bank.statement.provider"]._fints_split_iban
        self.assertEqual(
            split("GB33BUKB20201555555555ACME Ltd"),
            ("GB33BUKB20201555555555", "ACME Ltd"),
        )
        self.assertEqual(split("Some Customer"), (None, "Some Customer"))

    @freeze_time("2026-10-15 10:00:00")
    def test_pull_local_dates(self):
        """A pull from 01.10. 00:00 until 02.10. 00:00 Europe/Berlin, as entered
        in the pull wizard, only fetches 01.10."""
        self.provider.action_fints_connect()
        self.bank.fetched.clear()
        self.provider._pull(datetime(2026, 9, 30, 22), datetime(2026, 10, 1, 22))
        self.assertEqual(
            self.bank.fetched,
            [(IBAN, datetime(2026, 10, 1).date(), datetime(2026, 10, 1).date())],
        )
        self.assertEqual(len(self._statement_lines()), 3)

    def test_mt940_balances_several_days(self):
        """The bank reports the balances per day, the opening balance of the
        period is the one of the first day"""
        second_day = (
            ":20:STARTUMS\n:25:37040044/0532013000\n:28C:0\n"
            ":60F:C261002EUR1090,20\n"
            ":61:2610021002CR10,00NTRFNONREF\n:86:166?00SEPA-GUTSCHRIFT?20Rent\n"
            ":62F:C261002EUR1100,20\n-"
        )
        transactions = mt940_to_array(self._mt940_sample() + "\n" + second_day)
        lines = [self.provider._fints_prepare_mt940_line(t.data) for t in transactions]
        self.assertEqual(len(lines), 4)
        balance_end = self.provider._fints_mt940_balance_end(transactions)
        self.assertEqual(
            self.provider._fints_statement_balances(lines, balance_end),
            {
                "balance_start": Decimal("1000.00"),
                "balance_end_real": Decimal("1100.20"),
            },
        )

    def test_balances_not_reported(self):
        mt940 = self._mt940_sample().replace(":62F:C261001EUR1090,20\n", "")
        self.assertIsNone(self.provider._fints_mt940_balance_end(mt940_to_array(mt940)))
        self.assertIsNone(self.provider._fints_mt940_balance_end([]))
        with file_open(
            "account_statement_import_online_fints/tests/samples/camt052.xml", "rb"
        ) as f:
            camt = f.read().replace(b"<Cd>CLBD</Cd>", b"<Cd>XXXX</Cd>")
        self.assertIsNone(self.provider._fints_camt_balance_end([camt]))
        self.assertEqual(self.provider._fints_statement_balances([], None), {})

    def test_prepare_mt940_line_padded(self):
        """Some banks pad the fields with spaces"""
        line = self.provider._fints_prepare_mt940_line(
            {
                "date": datetime(2026, 10, 13).date(),
                "amount": SimpleNamespace(amount=1190),
                "purpose": "ReNr MT/2026/0372 ",
                "end_to_end_reference": "NOTPROVIDED               ",
                "customer_reference": "NONREF  ",
                "applicant_name": "Katana Sec GmbH  ",
                "applicant_iban": "DE11701695980001101404",
                "posting_text": "EURO-Ueberweisung",
            }
        )
        self.assertEqual(line["payment_ref"], "ReNr MT/2026/0372")
        self.assertFalse(line["ref"])
        self.assertEqual(line["partner_name"], "Katana Sec GmbH")
        self.assertNotIn("NOTPROVIDED", line["narration"])
        line = self.provider._fints_prepare_mt940_line(
            {
                "date": datetime(2026, 10, 13).date(),
                "amount": SimpleNamespace(amount=-10),
                "customer_reference": "2700142                  ",
            }
        )
        self.assertEqual(line["ref"], "2700142")
        line = self.provider._fints_prepare_mt940_line(
            {
                "date": datetime(2026, 10, 13).date(),
                "amount": SimpleNamespace(amount=-10),
                "customer_reference": "NONREF\nNONREF",
            }
        )
        self.assertFalse(line["ref"])
