# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64decode, b64encode
from datetime import timedelta
from decimal import Decimal
from time import monotonic, sleep

from fints.client import NeedTANResponse
from fints.exceptions import FinTSSCARequiredError
from lxml import etree
from stdnum import iban

from odoo import api, fields, models
from odoo.exceptions import UserError

from .fints_client import FinTS3PinTanClient


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    # The PIN gives access to the bank account. Only for administrators,
    # accessed with sudo.
    password = fields.Char(groups="base.group_system")
    fints_blz = fields.Char(string="Bank Code (BLZ)")
    fints_customer_id = fields.Char(
        string="Customer ID",
        help="Only needed if your bank uses a customer ID that differs "
        "from the login name.",
    )
    fints_product_id = fields.Char(
        string="FinTS Product ID",
        help="Registration number of the FinTS product, assigned for free by "
        "Die Deutsche Kreditwirtschaft (https://www.fints.org).",
    )
    fints_tan_mechanism = fields.Char(
        string="TAN Method",
        help="Code of the TAN method (security function) to use, see the "
        "available TAN methods. Leave empty to select one automatically.",
    )
    fints_tan_mechanisms = fields.Text(
        string="Available TAN Methods",
        readonly=True,
        copy=False,
    )
    fints_tan_medium = fields.Char(
        string="TAN Medium",
        help="Name of the TAN medium (e.g. the device of the banking app), "
        "only needed if your bank asks for one.",
    )
    fints_confirmation_timeout = fields.Integer(
        string="Wait for App Confirmation (Minutes)",
        help="For banks asking to confirm each access in the banking app: "
        "time a pull waits for the confirmation. 0 means a pull fails "
        "and the provider has to be connected again.",
    )
    fints_state = fields.Selection(
        selection=[
            ("disconnected", "Not Connected"),
            ("tan_required", "Confirmation Required"),
            ("connected", "Connected"),
        ],
        string="FinTS Connection",
        default="disconnected",
        readonly=True,
        copy=False,
    )
    # Opaque state of the FinTS client (system id, bank and user parameter
    # data, the latter including the account numbers and names). The strong
    # customer authentication is bound to the system id, so it has to be kept
    # between the pulls. Only for administrators, accessed with sudo.
    fints_client_data = fields.Binary(
        attachment=False, copy=False, groups="base.group_system"
    )
    # Types of the commands the bank only accepts with a TAN segment, whatever
    # its parameters announce, comma separated
    fints_tan_segment_types = fields.Char(readonly=True, copy=False)

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [("fints", "FinTS")]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "fints":
            return super()._obtain_statement_data(date_since, date_until)
        return self._fints_obtain_statement_data(date_since, date_until)

    def _fints_get_client_class(self):
        """Hook for extension: return the python-fints client class, e.g. one
        with corrections for a specific bank"""
        self.ensure_one()
        return FinTS3PinTanClient

    def _fints_get_client(self):
        self.ensure_one()
        if not self.fints_product_id:
            raise UserError(
                self.env._("Set the FinTS product ID of provider %s first.", self.name)
            )
        client_data = self.sudo().fints_client_data
        client = self._fints_get_client_class()(
            self.fints_blz,
            self.username,
            self.sudo().password,
            self.api_base,
            customer_id=self.fints_customer_id or None,
            product_id=self.fints_product_id,
            from_data=b64decode(client_data) if client_data else None,
        )
        if self.fints_tan_medium:
            client.selected_tan_medium = self.fints_tan_medium
        if self.fints_tan_segment_types:
            client.tan_segment_types = frozenset(
                self.fints_tan_segment_types.split(",")
            )
        return client

    def _fints_store_client(self, client, state=None):
        self.ensure_one()
        vals = {
            "fints_tan_segment_types": ",".join(sorted(client.tan_segment_types))
            or False,
        }
        if state:
            vals["fints_state"] = state
        self.write(vals)
        self.sudo().fints_client_data = b64encode(
            client.deconstruct(including_private=True)
        )

    def _fints_select_tan_mechanism(self, client):
        """Fetch the TAN methods of the bank and select the configured one"""
        self.ensure_one()
        client.fetch_tan_mechanisms()
        mechanisms = client.get_tan_mechanisms()
        self.fints_tan_mechanisms = "\n".join(
            f"{code}: {mechanism.name}" for code, mechanism in mechanisms.items()
        )
        if self.fints_tan_mechanism:
            if self.fints_tan_mechanism not in mechanisms:
                raise UserError(
                    self.env._(
                        "The bank does not offer the TAN method %s.",
                        self.fints_tan_mechanism,
                    )
                )
            client.set_tan_mechanism(self.fints_tan_mechanism)
        elif mechanisms and client.get_current_tan_mechanism() not in mechanisms:
            # python-fints keeps the one step method (999) if the bank allows
            # it for the user, use the first TAN method instead
            client.set_tan_mechanism(next(iter(mechanisms)))
        if (
            not self.fints_tan_medium
            and client.get_current_tan_mechanism() in mechanisms
            and client.is_tan_media_required()
        ):
            __, media = client.get_tan_media()
            if media:
                self.fints_tan_medium = media[0].tan_medium_name
                client.selected_tan_medium = self.fints_tan_medium

    def _fints_get_account(self, accounts):
        self.ensure_one()
        for account in accounts:
            if (
                self.journal_id._sanitize_bank_account_number(account.iban)
                == self.account_number
            ):
                return account
        raise UserError(
            self.env._(
                "The bank account %(account)s is not available with the FinTS "
                "login of provider %(provider)s.",
                account=self.account_number,
                provider=self.name,
            )
        )

    def _fints_continue_connect(self, client, response=None):
        """Continue the connection within the standing dialog of the client.

        :param response: the response to the last command, None or the
            response to the dialog initialization when nothing was sent yet
        :return: a NeedTANResponse if the bank asks for a confirmation
        """
        self.ensure_one()
        if not isinstance(response, list):
            response = client.get_sepa_accounts()
            if isinstance(response, NeedTANResponse):
                return response
        account = self._fints_get_account(response)
        # Some banks only ask for the confirmation when fetching the
        # transactions, ask for it now instead of failing the next pull
        today = self._utc_to_provider_tz(fields.Datetime.now()).date()
        response = self._fints_get_transactions(client, account, today, today)
        if isinstance(response, NeedTANResponse):
            # The confirmed check is not continued, the connection starts over
            response.resume_method = "_continue_check_transactions_access"
            return response
        return None

    def _fints_get_transactions(self, client, account, start_date, end_date):
        self.ensure_one()
        if self._fints_supports_mt940(client):
            return client.get_transactions(account, start_date, end_date)
        return client.get_transactions_xml(account, start_date, end_date)

    def action_fints_connect(self):
        """Connect to the bank, confirming the access with a TAN if needed"""
        self.ensure_one()
        client = self._fints_get_client()
        self._fints_select_tan_mechanism(client)
        self.message_subscribe(partner_ids=self.env.user.partner_id.ids)
        with client:
            response = client.init_tan_response or self._fints_continue_connect(client)
            if response:
                dialog_data = client.pause_dialog()
        if response:
            return self._fints_request_tan(client, response, dialog_data)
        return self._fints_connected(client)

    def action_fints_disconnect(self):
        """Forget the FinTS client state, e.g. to change the login"""
        self.write(
            {
                "fints_state": "disconnected",
                "fints_tan_mechanisms": False,
                "fints_tan_segment_types": False,
            }
        )
        self.sudo().fints_client_data = False

    def _fints_request_tan(self, client, response, dialog_data):
        """Pause the connection and ask the user for the confirmation"""
        self.ensure_one()
        self._fints_store_client(client, "tan_required")
        Wizard = self.env["online.bank.statement.fints.tan"]
        tan_data = response.get_data()
        wizard = Wizard.create(
            {
                "provider_id": self.id,
                "dialog_data": b64encode(dialog_data),
                "tan_data": b64encode(tan_data),
                "signature": Wizard._get_signature(self, dialog_data, tan_data),
                # The decoupled flag gets lost by NeedTANResponse.get_data()
                "decoupled": response.decoupled,
                "challenge": response.challenge_html,
                "challenge_image": b64encode(response.challenge_matrix[1])
                if response.challenge_matrix
                else False,
                "challenge_hhduc": response.challenge_hhduc,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Confirm Bank Access"),
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _fints_connected(self, client):
        self.ensure_one()
        self._fints_store_client(client, "connected")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._("Connected to the bank."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _fints_tan_required(self):
        """Inform the followers, once, that the access needs a confirmation"""
        self.ensure_one()
        if self.fints_state != "tan_required":
            self.fints_state = "tan_required"
            self.message_post(
                body=self.env._(
                    "The bank asks to confirm the access again. Click on "
                    "'Connect' to confirm it, until then no statements are "
                    "pulled."
                ),
                subtype_xmlid="mail.mt_comment",
            )

    def _fints_obtain_statement_data(self, date_since, date_until):
        """Translate the transactions booked from date_since until date_until
        (exclusive) into statement line values"""
        self.ensure_one()
        # FinTS only knows the dates of the bank and rejects end dates in the
        # future
        start_date = self._utc_to_provider_tz(date_since).date()
        end_date = min(
            self._utc_to_provider_tz(date_until - timedelta(seconds=1)).date(),
            self._utc_to_provider_tz(fields.Datetime.now()).date(),
        )
        if start_date > end_date:
            return [], {}
        if self.fints_state != "connected":
            raise UserError(
                self.env._(
                    "Provider %s is not connected to the bank, click on 'Connect'.",
                    self.name,
                )
            )
        client = self._fints_get_client()
        try:
            with client:
                response = client.init_tan_response
                if response:
                    response = self._fints_wait_confirmation(client, response)
                if not isinstance(response, NeedTANResponse):
                    response = self._fints_wait_confirmation(
                        client, client.get_sepa_accounts()
                    )
                if not isinstance(response, NeedTANResponse):
                    account = self._fints_get_account(response)
                    response = self._fints_wait_confirmation(
                        client,
                        self._fints_get_transactions(
                            client, account, start_date, end_date
                        ),
                    )
        except FinTSSCARequiredError:
            # Some banks ask for the confirmation of the access by rejecting
            # a command instead of asking for a TAN
            response = None
            sca_required = True
        else:
            sca_required = False
        self._fints_store_client(client)
        if sca_required:
            self._fints_tan_required()
            raise UserError(
                self.env._(
                    "The bank asks to confirm the access of provider %s again.",
                    self.name,
                )
            )
        if isinstance(response, NeedTANResponse):
            if response.decoupled and self.fints_confirmation_timeout:
                # Missed the confirmation of this pull, the next one asks again
                raise UserError(
                    self.env._(
                        "The access of provider %s was not confirmed in the "
                        "banking app in time.",
                        self.name,
                    )
                )
            self._fints_tan_required()
            raise UserError(
                self.env._(
                    "The bank asks to confirm the access of provider %s again.",
                    self.name,
                )
            )
        if self._fints_supports_mt940(client):
            lines = [self._fints_prepare_mt940_line(t.data) for t in response]
            balance_end = self._fints_mt940_balance_end(response)
        else:
            booked_streams, __ = response
            lines = self._fints_parse_camt(booked_streams)
            balance_end = self._fints_camt_balance_end(booked_streams)
        return lines, self._fints_statement_balances(lines, balance_end)

    @api.model
    def _fints_statement_balances(self, lines, balance_end):
        """Return the balances of the statement period from the closing
        balance reported by the bank. The opening balance is computed from the
        lines: the bank reports one per statement (day), only the one of the
        first statement fits the period.
        """
        if balance_end is None:
            return {}
        balance_end = Decimal(str(balance_end))
        return {
            "balance_start": balance_end
            - sum(Decimal(str(line["amount"])) for line in lines),
            "balance_end_real": balance_end,
        }

    def _fints_wait_confirmation(self, client, response):
        """Wait for the confirmation of a decoupled TAN request in the banking
        app, if configured, polling the bank as allowed by its parameters"""
        self.ensure_one()
        if (
            not isinstance(response, NeedTANResponse)
            or not response.decoupled
            or not self.fints_confirmation_timeout
        ):
            return response
        mechanism = client.get_tan_mechanisms()[client.get_current_tan_mechanism()]
        wait = getattr(mechanism, "wait_before_first_poll", None) or 5
        wait_next = getattr(mechanism, "wait_before_next_poll", None) or 2
        max_polls = getattr(mechanism, "decoupled_max_poll_number", None)
        deadline = monotonic() + self.fints_confirmation_timeout * 60
        polls = 0
        while isinstance(response, NeedTANResponse) and monotonic() + wait < deadline:
            if max_polls and polls >= max_polls:
                break
            sleep(wait)
            response = client.send_tan(response, "")
            polls += 1
            wait = wait_next
        return response

    @api.model
    def _fints_supports_mt940(self, client):
        return bool(client.bpd.find_segment_first("HIKAZS"))

    def _fints_prepare_mt940_line(self, data):
        """Translate a MT940 transaction into statement line values"""
        self.ensure_one()
        # Some banks pad the fields with spaces
        data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in data.items()
        }
        date = data.get("guessed_entry_date") or data.get("entry_date") or data["date"]
        purpose = " ".join(
            filter(None, [data.get("purpose"), data.get("additional_purpose")])
        )
        end_to_end_reference = self._fints_mt940_reference(
            data.get("end_to_end_reference")
        )
        ref = end_to_end_reference or self._fints_mt940_reference(
            data.get("customer_reference")
        )
        narration = {
            self.env._("Posting Text"): data.get("posting_text"),
            self.env._("Purpose"): purpose,
            self.env._("End to End Reference"): end_to_end_reference,
            self.env._("Creditor ID"): data.get("applicant_creditor_id"),
            self.env._("Mandate Reference"): data.get("additional_position_reference"),
            self.env._("Bank Reference"): data.get("bank_reference"),
        }
        partner_name = data.get("applicant_name")
        account_number = data.get("applicant_iban")
        if not account_number and partner_name:
            account_number, partner_name = self._fints_split_iban(partner_name)
        return {
            "date": fields.Date.to_string(date),
            "amount": float(data["amount"].amount),
            "payment_ref": purpose or data.get("posting_text") or "/",
            "ref": ref or False,
            "partner_name": partner_name or False,
            "account_number": account_number or False,
            "transaction_type": data.get("transaction_code") or False,
            "narration": "\n".join(
                f"{key}: {value}" for key, value in narration.items() if value
            ),
        }

    @api.model
    def _fints_mt940_reference(self, reference):
        """Return the reference, or None if it is only made of placeholders
        (e.g. "NONREF" sent twice on separate lines)"""
        placeholders = {"NOTPROVIDED", "NONREF"}
        if not reference or set(reference.split()) <= placeholders:
            return None
        return reference

    @api.model
    def _fints_split_iban(self, name):
        """Split the IBAN of the counterparty from the start of its name.

        python-fints parses MT940 with the defaults of the mt940 library,
        which join the IBAN of the counterparty (field ?31) and its name
        (fields ?32 and ?33) in applicant_name, e.g.
        "DE02120300000000202051Some Customer", and leave applicant_iban empty.

        The prefixes of the name are checked from the longest (34) to the
        shortest (15) possible IBAN length, the first valid IBAN is split off.
        Checking the longest first avoids that a shorter valid prefix leaves
        digits of the IBAN in the name. A name without IBAN practically never
        starts with a valid one, as the country code, length and check digits
        have to match.

        :param name: the name of the counterparty as parsed by mt940
        :return: the IBAN, or None if the name does not start with one, and
            the name
        """
        for length in range(34, 14, -1):
            if iban.is_valid(name[:length]):
                return name[:length], name[length:].strip()
        return None, name

    @api.model
    def _fints_mt940_balance_end(self, transactions):
        """Return the closing balance of the last statement, if any. The mt940
        library keeps the balances of the last statement on the transactions.
        """
        if not transactions:
            return None
        closing = transactions[0].transactions.data.get("final_closing_balance")
        return closing.amount.amount if closing else None

    @api.model
    def _fints_camt_balance_end(self, streams):
        """Return the closing balance of the last report, if any. The CAMT
        parser returns 0 for a missing balance, so check its presence first.
        """
        if not streams:
            return None
        parser = self.env["account.statement.import.camt.parser"]
        root = etree.fromstring(streams[-1])
        ns = root.tag[1 : root.tag.index("}")]
        node = root[0][-1]
        if not node.xpath(
            './ns:Bal/ns:Tp/ns:CdOrPrtry/ns:Cd[text()="CLBD" or text()="ITBD"]',
            namespaces={"ns": ns},
        ):
            return None
        return parser.get_balance_amounts(ns, node)[1]

    def _fints_parse_camt(self, streams):
        self.ensure_one()
        parser = self.env["account.statement.import.camt.parser"]
        lines = []
        for stream in streams:
            __, __, statements = parser.parse(stream)
            for statement in statements:
                lines += statement["transactions"]
        return lines
