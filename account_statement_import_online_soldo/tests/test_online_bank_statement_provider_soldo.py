# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon

from ..models.online_bank_statement_provider_soldo import SOLDO_ATTACHMENT_MAX_SIZE

MODULE = (
    "odoo.addons.account_statement_import_online_soldo.models."
    "online_bank_statement_provider_soldo"
)
PROVIDER = f"{MODULE}.OnlineBankStatementProviderSoldo"


def soldo_transaction(transaction_id, **values):
    transaction = {
        "id": transaction_id,
        "tx_id": f"TX-{transaction_id}",
        "status": "Settled",
        "category": "Payment",
        "transaction_sign": "Negative",
        "amount": 52.0,
        "amount_currency": "EUR",
        "tx_amount": 52.0,
        "tx_amount_currency": "EUR",
        "date": "2026-03-10T09:15:00Z",
        "settlement_date": "2026-03-12T00:00:00Z",
        "wallet_id": "wallet-1",
        "wallet_name": "Fleet card",
        "merchant": {"id": 2100846839, "name": "FUEL STATION"},
        "notes": "Van refuel",
    }
    transaction.update(values)
    return transaction


class TestOnlineBankStatementProviderSoldo(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = cls.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()
        cls.eur = cls.env.ref("base.EUR")
        cls.eur.active = True
        cls.usd = cls.env.ref("base.USD")
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Soldo",
                "type": "bank",
                "code": "SOLDO",
                "currency_id": cls.eur.id,
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "name": "Soldo",
                "service": "soldo",
                "journal_id": cls.journal.id,
                "username": "CLIENT-ID",
                "password": "CLIENT-SECRET",
                "passphrase": "FINGERPRINT-TOKEN",
                "certificate_private_key": pem,
                # The statement periods start at midnight in this time zone
                "tz": "UTC",
            }
        )

    def _mock_api(self, transactions, pages=1):
        """Fake Soldo API: the token, then the transactions split in pages."""
        calls = []

        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == "/oauth/authorize":
                return {"access_token": "TOKEN"}
            page = kwargs["params"]["p"]
            size = -(-len(transactions) // pages) if transactions else 0
            return {
                "current_page": page,
                "pages": pages,
                "results": transactions[page * size : (page + 1) * size],
            }

        return patch(f"{PROVIDER}._soldo_request", side_effect=request), calls

    def _obtain_lines(self, transactions, date_since, date_until, pages=1):
        mock, calls = self._mock_api(transactions, pages)
        with mock:
            lines, values = self.provider._obtain_statement_data(date_since, date_until)
        self.assertEqual(values, {})
        return lines, calls

    def test_fingerprint_headers(self):
        headers = self.provider._soldo_fingerprint_headers(
            "TOKEN", ["2026-03-01", "2026-03-29"]
        )
        fingerprint = hashlib.sha512(
            b"2026-03-012026-03-29FINGERPRINT-TOKEN"
        ).hexdigest()
        self.assertEqual(headers["Authorization"], "Bearer TOKEN")
        self.assertEqual(headers["X-Soldo-Fingerprint"], fingerprint)
        # Raises if the signature does not match
        self.private_key.public_key().verify(
            base64.b64decode(headers["X-Soldo-Fingerprint-Signature"]),
            fingerprint.encode(),
            padding.PKCS1v15(),
            hashes.SHA512(),
        )

    def test_invalid_private_key(self):
        self.provider.certificate_private_key = "not a key"
        with self.assertRaises(UserError):
            self.provider._soldo_fingerprint_headers("TOKEN", [])

    def test_private_key_not_shown(self):
        # A saved key is not read back, only reported as saved
        self.assertFalse(self.provider.soldo_private_key)
        self.assertTrue(self.provider.soldo_private_key_set)
        key = self.provider.certificate_private_key
        # Saving the form with the field left empty keeps the key
        self.provider.soldo_private_key = False
        self.assertEqual(self.provider.certificate_private_key, key)
        # A new key replaces it
        self.provider.soldo_private_key = "NEW KEY"
        self.assertEqual(self.provider.certificate_private_key, "NEW KEY")
        # Read again, as the form does after saving
        self.provider.invalidate_recordset()
        self.assertFalse(self.provider.soldo_private_key)

    def test_settled_transactions(self):
        lines, calls = self._obtain_lines(
            [
                soldo_transaction("T1"),
                soldo_transaction("T2", status="Authorised"),
                soldo_transaction("T3", status="Declined"),
                soldo_transaction(
                    "T4",
                    category="Wallet",
                    transaction_sign="Positive",
                    amount=700.0,
                    tx_amount=700.0,
                    merchant={},
                ),
            ],
            datetime(2026, 3, 12),
            datetime(2026, 3, 13),
        )
        self.assertEqual([line["unique_import_id"] for line in lines], ["T1", "T4"])
        payment, top_up = lines
        self.assertEqual(payment["date"], datetime(2026, 3, 12))
        self.assertEqual(payment["amount"], -52.0)
        self.assertEqual(payment["payment_ref"], "FUEL STATION")
        self.assertEqual(payment["partner_name"], "FUEL STATION")
        self.assertEqual(payment["ref"], "TX-T1")
        self.assertEqual(payment["transaction_type"], "Payment")
        self.assertEqual(payment["narration"], "<p>Van refuel</p>")
        self.assertNotIn("foreign_currency_id", payment)
        self.assertEqual(json.loads(payment["raw_data"])["id"], "T1")
        self.assertEqual(top_up["amount"], 700.0)
        self.assertEqual(top_up["payment_ref"], "Wallet")
        self.assertFalse(top_up["partner_name"])
        # Searched from the days to settlement before the period
        method, path, kwargs = calls[1]
        self.assertEqual((method, path), ("get", "/business/v2/transactions"))
        self.assertEqual(kwargs["params"]["fromDate"], "2026-03-02T00:00:00Z")
        self.assertEqual(kwargs["params"]["toDate"], "2026-03-13T00:00:00Z")

    def test_authorised_transactions(self):
        self.provider.soldo_import_state = "authorised"
        lines, calls = self._obtain_lines(
            [
                soldo_transaction("T1"),
                soldo_transaction("T2", status="Authorised", settlement_date=None),
                soldo_transaction("T3", status="Cancelled"),
            ],
            datetime(2026, 3, 10),
            datetime(2026, 3, 11),
        )
        self.assertEqual([line["unique_import_id"] for line in lines], ["T1", "T2"])
        self.assertEqual(lines[0]["date"], datetime(2026, 3, 10, 9, 15))
        self.assertEqual(calls[1][2]["params"]["fromDate"], "2026-03-10T00:00:00Z")

    def test_excluded_wallets_and_currency(self):
        self.provider.soldo_excluded_wallets = "Company wallet, wallet-3"
        lines, _calls = self._obtain_lines(
            [
                soldo_transaction("T1"),
                soldo_transaction("T2", wallet_name="Company wallet"),
                soldo_transaction("T3", wallet_id="wallet-3"),
                soldo_transaction("T4", amount_currency="GBP"),
            ],
            datetime(2026, 3, 12),
            datetime(2026, 3, 13),
        )
        self.assertEqual([line["unique_import_id"] for line in lines], ["T1"])

    def test_foreign_currency(self):
        self.usd.active = True
        lines, _calls = self._obtain_lines(
            [soldo_transaction("T1", tx_amount=56.3, tx_amount_currency="USD")],
            datetime(2026, 3, 12),
            datetime(2026, 3, 13),
        )
        self.assertEqual(lines[0]["amount"], -52.0)
        self.assertEqual(lines[0]["foreign_currency_id"], self.usd.id)
        self.assertEqual(lines[0]["amount_currency"], -56.3)

    def test_fee(self):
        lines, _calls = self._obtain_lines(
            [soldo_transaction("T1", fee_amount=1.5, fee_currency="EUR")],
            datetime(2026, 3, 12),
            datetime(2026, 3, 13),
        )
        payment, fee = lines
        self.assertEqual(fee["unique_import_id"], "T1-FEE")
        self.assertEqual(fee["amount"], -1.5)
        self.assertEqual(fee["partner_name"], "Soldo")
        self.assertEqual(fee["date"], payment["date"])

    def test_intervals_and_pages(self):
        transactions = [soldo_transaction(f"T{index}") for index in range(5)]
        lines, calls = self._obtain_lines(
            transactions, datetime(2026, 1, 1), datetime(2026, 3, 1), pages=2
        )
        searches = [call[2]["params"] for call in calls[1:]]
        # From the days to settlement before the period, in intervals of at
        # most 29 days, each read page by page; a transaction found in more
        # intervals gives its lines once
        self.assertEqual(
            [
                (params["fromDate"], params["toDate"], params["p"])
                for params in searches
            ],
            [
                ("2025-12-22T00:00:00Z", "2026-01-20T00:00:00Z", 0),
                ("2025-12-22T00:00:00Z", "2026-01-20T00:00:00Z", 1),
                ("2026-01-20T00:00:00Z", "2026-02-18T00:00:00Z", 0),
                ("2026-01-20T00:00:00Z", "2026-02-18T00:00:00Z", 1),
                ("2026-02-18T00:00:00Z", "2026-03-01T00:00:00Z", 0),
                ("2026-02-18T00:00:00Z", "2026-03-01T00:00:00Z", 1),
            ],
        )
        self.assertEqual(len(lines), 5)

    def test_request_error(self):
        response = MagicMock(ok=False, status_code=401, text="Unauthorized")
        response.json.return_value = {"message": "INVALID_TOKEN"}
        with patch(f"{MODULE}.requests.request", return_value=response):
            with self.assertRaisesRegex(UserError, "INVALID_TOKEN"):
                self.provider._soldo_get_access_token()

    def test_access_token(self):
        response = MagicMock(ok=True)
        response.json.return_value = {"access_token": "TOKEN"}
        with patch(f"{MODULE}.requests.request", return_value=response) as request:
            self.assertEqual(self.provider._soldo_get_access_token(), "TOKEN")
        args, kwargs = request.call_args
        self.assertEqual(args, ("post", "https://api.soldo.com/oauth/authorize"))
        self.assertEqual(
            kwargs["data"],
            {"client_id": "CLIENT-ID", "client_secret": "CLIENT-SECRET"},
        )
        self.assertTrue(kwargs["timeout"])

    def test_notes(self):
        lines, _calls = self._obtain_lines(
            [
                soldo_transaction("T1", user_notes="Receipt lost"),
                soldo_transaction("T2", notes="", user_notes=" "),
            ],
            datetime(2026, 3, 12),
            datetime(2026, 3, 13),
        )
        # The notes of the card user follow the ones of the transaction
        self.assertEqual(lines[0]["narration"], "<p>Van refuel<br/>Receipt lost</p>")
        self.assertFalse(lines[1]["narration"])

    def test_pull(self):
        mock, _calls = self._mock_api(
            [
                soldo_transaction(
                    "T1",
                    fee_amount=1.5,
                    fee_currency="EUR",
                    merchant_category={"mcc": "5541", "mcc_description": "Fuel"},
                    direct_url="https://soldo.example/T1",
                )
            ]
        )
        self.provider.company_id.partner_id.tz = "Europe/Rome"
        with mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        lines = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(len(lines), 2)
        line = lines.filtered(lambda line: line.amount == -52.0)
        self.assertEqual(line.partner_name, "FUEL STATION")
        # The details of the transaction are logged once in the chatter of the
        # journal entry of the transaction, not on the fee
        messages = line.move_id.message_ids.filtered(
            lambda message: "Soldo transaction" in (message.body or "")
        )
        self.assertEqual(len(messages), 1)
        for text in ("FUEL STATION", "5541 - Fuel", "Van refuel", "TX-T1"):
            self.assertIn(text, messages.body)
        self.assertIn('href="https://soldo.example/T1"', messages.body)
        # The dates are in the time zone of the company: 09:15 UTC
        self.assertIn("10:15", messages.body)
        fee_messages = (lines - line).move_id.message_ids.filtered(
            lambda message: "Soldo transaction" in (message.body or "")
        )
        self.assertFalse(fee_messages)

    def _mock_attachments_api(self, transactions, attachments, updated_transactions=()):
        """Fake Soldo API with the attachments of the transactions."""
        calls = []

        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == "/oauth/authorize":
                return {"access_token": "TOKEN"}
            if path.endswith("/attachments"):
                transaction_id = path.split("/")[-2]
                if transaction_id not in attachments:
                    # As raised by _soldo_request on an error of the API
                    message = "Soldo API call failed: NOT_FOUND"
                    raise UserError(message)
                return {"attachments": attachments[transaction_id]}
            if kwargs["params"].get("dateType") == "UPDATE":
                results = updated_transactions
            else:
                results = transactions
            return {"current_page": 0, "pages": 1, "results": results}

        def download(url, timeout):
            if url == "broken":
                raise requests.ConnectionError("unreachable")
            return MagicMock(content=url.encode())

        return (
            patch(f"{PROVIDER}._soldo_request", side_effect=request),
            patch(f"{MODULE}.requests.get", side_effect=download),
            calls,
        )

    def _mock_update_api(self, transactions, updated_transactions):
        """Fake Soldo API: the transactions of the period, or the ones changed
        during the period when searched by update date."""
        calls = []

        def request(method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path == "/oauth/authorize":
                return {"access_token": "TOKEN"}
            if kwargs["params"].get("dateType") == "UPDATE":
                results = updated_transactions
            else:
                results = transactions
            return {"current_page": 0, "pages": 1, "results": results}

        return patch(f"{PROVIDER}._soldo_request", side_effect=request), calls

    def _move_attachments(self, unique_import_id):
        line = self.env["account.bank.statement.line"].search(
            [("unique_import_id", "=like", f"%-{unique_import_id}")]
        )
        self.assertEqual(len(line), 1)
        return self.env["ir.attachment"].search(
            [("res_model", "=", "account.move"), ("res_id", "=", line.move_id.id)]
        )

    @mute_logger(MODULE)
    def test_attachments(self):
        self.provider.soldo_attachments = True
        transactions = [
            soldo_transaction("T1", has_attachments=True, fee_amount=1.0),
            soldo_transaction("T2", has_attachments=True),
            soldo_transaction("T3"),
            soldo_transaction("T4", has_attachments=True),
        ]
        attachments = {
            "T1": [
                {"file_name": "receipt.jpg", "file_size": 7, "url": "content"},
                {"file_name": "invoice.pdf", "url": "broken"},
            ],
            "T2": [
                {
                    "file_name": "huge.pdf",
                    "file_size": SOLDO_ATTACHMENT_MAX_SIZE + 1,
                    "url": "huge",
                }
            ],
        }
        request_mock, download_mock, calls = self._mock_attachments_api(
            transactions, attachments
        )
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        receipt = self._move_attachments("T1")
        self.assertEqual(receipt.name, "receipt.jpg")
        self.assertEqual(receipt.raw, b"content")
        self.assertFalse(self._move_attachments("T1-FEE"))
        self.assertFalse(self._move_attachments("T2"))
        self.assertFalse(self._move_attachments("T3"))
        self.assertFalse(self._move_attachments("T4"))
        attachment_calls = {
            call[1]: call[2]["headers"]
            for call in calls
            if call[1].endswith("attachments")
        }
        self.assertEqual(
            set(attachment_calls),
            {
                "/business/v2/transactions/T1/attachments",
                "/business/v2/transactions/T2/attachments",
                "/business/v2/transactions/T4/attachments",
            },
        )
        # An attachment request needs the token, not the signature
        self.assertEqual(
            attachment_calls["/business/v2/transactions/T1/attachments"],
            {"Authorization": "Bearer TOKEN"},
        )
        # The failures are reported on the provider
        message = str(self.provider.message_ids[:1].body)
        self.assertIn("unreachable", message)
        self.assertIn("huge.pdf", message)
        self.assertIn("NOT_FOUND", message)
        # A second pull does not import the attachments again
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        self.assertEqual(len(self._move_attachments("T1")), 1)

    def test_attachments_disabled(self):
        request_mock, download_mock, calls = self._mock_attachments_api(
            [soldo_transaction("T1", has_attachments=True)],
            {"T1": [{"file_name": "receipt.jpg", "url": "content"}]},
        )
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        self.assertFalse(self._move_attachments("T1"))
        self.assertFalse([call for call in calls if call[1].endswith("attachments")])

    def test_attachments_added_later(self):
        self.provider.soldo_attachments = True
        transaction = soldo_transaction("T1", has_attachments=True)
        attachments = {
            "T1": [{"attachment_id": "A1", "file_name": "receipt.jpg", "url": "one"}]
        }
        request_mock, download_mock, _calls = self._mock_attachments_api(
            [transaction], attachments
        )
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        self.assertEqual(self._move_attachments("T1").mapped("name"), ["receipt.jpg"])
        # Days later the user attaches the invoice: the transaction is among the
        # ones updated in the period pulled
        attachments["T1"].append(
            {"attachment_id": "A2", "file_name": "invoice.pdf", "url": "two"}
        )
        request_mock, download_mock, calls = self._mock_attachments_api(
            [], attachments, updated_transactions=[transaction]
        )
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 20), datetime(2026, 3, 21))
        self.assertEqual(
            sorted(self._move_attachments("T1").mapped("name")),
            ["invoice.pdf", "receipt.jpg"],
        )
        update_search = [
            call[2]["params"]
            for call in calls
            if call[2].get("params", {}).get("dateType") == "UPDATE"
        ]
        self.assertEqual(update_search[0]["fromDate"], "2026-03-20T00:00:00Z")

    def _statement_line(self, transaction_id):
        return self.env["account.bank.statement.line"].search(
            [("unique_import_id", "=like", f"%-{transaction_id}")]
        )

    def test_update_lines(self):
        self.provider.soldo_import_state = "authorised"
        self.provider.soldo_update_lines = True
        transactions = [
            soldo_transaction("T1", status="Authorised"),
            soldo_transaction("T2", status="Authorised"),
            soldo_transaction("T3", status="Authorised"),
            soldo_transaction("T4", status="Authorised"),
        ]
        mock, _calls = self._mock_update_api(transactions, transactions)
        with mock:
            self.provider._pull(datetime(2026, 3, 10), datetime(2026, 3, 11))
        self.assertEqual(self._statement_line("T1").amount, -52.0)
        reconciled = self._statement_line("T2")
        reconciled.payment_ref = "Checked"
        # Reconciling for real needs a full chart of accounts
        reconciled.is_reconciled = True
        updated_transactions = [
            soldo_transaction(
                "T1",
                amount=55.0,
                tx_amount=55.0,
                merchant={"id": 1, "name": "FUEL STATION 2"},
                expense_category={"name": "Fuel"},
            ),
            soldo_transaction("T2", amount=60.0, tx_amount=60.0, notes="Checked"),
            soldo_transaction("T3", status="Cancelled"),
            # Changed for an internal value only: a file was attached
            soldo_transaction("T4", status="Authorised", has_attachments=True),
            soldo_transaction("T5"),
        ]
        # Other modules may write on the lines during the pull, and recompute
        # the reconciliation: keep the line reconciled as it would really be
        StatementLine = type(self.env["account.bank.statement.line"])
        compute_is_reconciled = StatementLine._compute_is_reconciled

        def keep_reconciled(lines):
            compute_is_reconciled(lines)
            lines.filtered(lambda line: line.id == reconciled.id).is_reconciled = True

        mock, calls = self._mock_update_api([], updated_transactions)
        with (
            mock,
            patch.object(StatementLine, "_compute_is_reconciled", keep_reconciled),
        ):
            self.provider._pull(datetime(2026, 3, 20), datetime(2026, 3, 21))
        searches = [
            call[2]["params"] for call in calls if call[1] != "/oauth/authorize"
        ]
        self.assertEqual(
            searches[-1],
            {
                "fromDate": "2026-03-20T00:00:00Z",
                "toDate": "2026-03-21T00:00:00Z",
                "dateType": "UPDATE",
                "p": 0,
                "s": 50,
            },
        )
        # A line not reconciled takes the new amount and label
        settled = self._statement_line("T1")
        self.assertEqual(settled.amount, -55.0)
        self.assertEqual(settled.payment_ref, "FUEL STATION 2")
        self.assertEqual(settled.partner_name, "FUEL STATION 2")
        self.assertEqual(
            json.loads(settled.raw_data)["expense_category"], {"name": "Fuel"}
        )
        # The new details are logged in the chatter of the journal entry
        updates = settled.move_id.message_ids.filtered(
            lambda message: "Soldo transaction updated" in (message.body or "")
        )
        self.assertEqual(len(updates), 1)
        self.assertIn("Fuel", updates.body)
        # A change that does not show in the details is not logged
        self.assertTrue(
            json.loads(self._statement_line("T4").raw_data)["has_attachments"]
        )
        self.assertFalse(
            self._statement_line("T4").move_id.message_ids.filtered(
                lambda message: "Soldo transaction updated" in (message.body or "")
            )
        )
        # A reconciled line keeps its amount and label, and is reported
        self.assertEqual(reconciled.amount, -52.0)
        self.assertEqual(reconciled.payment_ref, "Checked")
        self.assertEqual(json.loads(reconciled.raw_data)["notes"], "Checked")
        # A cancelled transaction is reported, its line is kept
        cancelled = self._statement_line("T3")
        self.assertEqual(cancelled.amount, -52.0)
        self.assertEqual(json.loads(cancelled.raw_data)["status"], "Authorised")
        message = str(self.provider.message_ids[:1].body)
        self.assertIn("60.0", message)
        self.assertIn("Cancelled", message)
        # A new transaction is not created
        self.assertFalse(self._statement_line("T5"))

    def test_attachments_and_update_one_search(self):
        self.provider.soldo_attachments = True
        self.provider.soldo_update_lines = True
        transaction = soldo_transaction("T1", has_attachments=True)
        attachments = {
            "T1": [{"attachment_id": "A1", "file_name": "receipt.jpg", "url": "one"}]
        }
        request_mock, download_mock, calls = self._mock_attachments_api(
            [transaction], attachments, updated_transactions=[transaction]
        )
        with request_mock, download_mock:
            self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
        self.assertEqual(self._move_attachments("T1").mapped("name"), ["receipt.jpg"])
        update_searches = [
            call
            for call in calls
            if call[2].get("params", {}).get("dateType") == "UPDATE"
        ]
        self.assertEqual(len(update_searches), 1)

    @mute_logger(
        "odoo.addons.account_statement_import_online.models."
        "online_bank_statement_provider"
    )
    def test_update_lines_error(self):
        self.provider.soldo_update_lines = True

        def request(method, path, **kwargs):
            if path == "/oauth/authorize":
                return {"access_token": "TOKEN"}
            if kwargs["params"].get("dateType") == "UPDATE":
                message = "Soldo API call failed: INTERVAL_TO_LARGE"
                raise UserError(message)
            return {"current_page": 0, "pages": 1, "results": []}

        with patch(f"{PROVIDER}._soldo_request", side_effect=request):
            with self.assertRaisesRegex(UserError, "INTERVAL_TO_LARGE"):
                self.provider._pull(datetime(2026, 3, 12), datetime(2026, 3, 13))
            # A scheduled pull reports the error on the provider
            self.provider.with_context(scheduled=True)._pull(
                datetime(2026, 3, 12), datetime(2026, 3, 13)
            )
        self.assertIn("INTERVAL_TO_LARGE", str(self.provider.message_ids[:1].body))
