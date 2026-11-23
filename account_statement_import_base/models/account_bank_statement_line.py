# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once
    # if the import format provides unique transaction IDs
    unique_import_id = fields.Char(string="Import ID", copy=False)
    raw_data = fields.Text(copy=False)

    # Details that many import formats and online providers give about the
    # counterpart and the payment, beyond the standard fields (partner_name,
    # account_number, transaction_type...), so that each of them does not
    # need its own fields.
    partner_email = fields.Char(string="Counterpart Email", copy=False)
    partner_phone = fields.Char(string="Counterpart Phone", copy=False)
    partner_street = fields.Char(string="Counterpart Street", copy=False)
    partner_zip = fields.Char(string="Counterpart Zip", copy=False)
    partner_city = fields.Char(string="Counterpart City", copy=False)
    partner_state_name = fields.Char(string="Counterpart State", copy=False)
    partner_country_id = fields.Many2one(
        comodel_name="res.country", string="Counterpart Country", copy=False
    )
    partner_external_ref = fields.Char(
        string="Counterpart Reference",
        copy=False,
        help="Reference of the counterpart at the provider, for instance the id "
        "of the customer, of the payer or of the merchant.",
    )
    payment_method_type = fields.Char(
        copy=False,
        help="Payment method, as named by the provider (card, sepa_debit, "
        "paypal...).",
    )
    card_masked_number = fields.Char(
        string="Card Number", copy=False, help="Masked number of the card."
    )
    card_expiry_date = fields.Date(
        copy=False, help="Last day of the month in which the card expires."
    )
    merchant_category = fields.Char(
        copy=False, help="Category of the merchant, for card payments."
    )
    subscription_ref = fields.Char(
        string="Subscription Reference",
        copy=False,
        help="Reference of the subscription or recurring payment at the provider.",
    )
    provider_url = fields.Char(
        string="Provider Link",
        copy=False,
        help="Link to the transaction on the website of the provider.",
    )

    _sql_constraints = [
        (
            "unique_import_id",
            "unique(unique_import_id)",
            "A bank account transaction can be imported only once!",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("raw_data") and not vals.get("transaction_details"):
                details = self._raw_data_to_transaction_details(vals["raw_data"])
                if details:
                    vals["transaction_details"] = details
        return super().create(vals_list)

    @api.model
    def _raw_data_to_transaction_details(self, raw_data):
        """Raw data for the standard transaction details, when it is JSON"""
        if not isinstance(raw_data, str):
            return False
        try:
            details = json.loads(raw_data)
        except ValueError:
            return False
        return details if isinstance(details, dict | list) else False
