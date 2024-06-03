# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import io
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from ofxparse import OfxParser
from ofxtools import ofxhome, utils
from ofxtools.Client import OFXClient, StmtRq

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OnlineBankStatementProviderOFX(models.Model):
    _inherit = "online.bank.statement.provider"

    ofx_institution_line_ids = fields.One2many("ofx.institution.line", "provider_id")

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("OFX", "OFX"),
        ]

    def get_statements(self, client, password, s1, try_no=1):
        statements = client.request_statements(password, s1, skip_profile=True)
        file_data = statements.read()
        if b"Request unsuccessful. Incapsula incident ID" in file_data and try_no <= 3:
            time.sleep(3)
            return self.get_statements(client, password, s1, try_no + 1)
        ofx = OfxParser.parse(io.BytesIO(file_data))
        if ofx.status.get("code") != 0:
            raise UserError(file_data)
        return ofx

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        is_scheduled = self.env.context.get("scheduled")
        # set date_until as today's date if its greter than today's date
        # to avoid failure of request.
        today = datetime.now()
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        if date_until > today:
            date_until = today
        if self.service != "OFX":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        lines = []
        if is_scheduled:
            ofx_institution_lines = self.ofx_institution_line_ids
        else:
            ofx_institution_lines = self.env["ofx.institution.line"].browse(
                self._context.get("ofx_institution_ids")
            )
        for ofx_institution_line in ofx_institution_lines:
            try:
                username = ofx_institution_line.username
                password = ofx_institution_line.password
                bankid = ofx_institution_line.bankid
                ofxhome_id = ofx_institution_line.institution_id.ofxhome_id
                acctid = ofx_institution_line.account_id

                institute = ofxhome.lookup(ofxhome_id)
                if institute is None or institute.url is None:
                    raise UserError(_("OFX Data is not available"))
                ofxhome_id = institute.id
                client = OFXClient(
                    institute.url,
                    userid=username,
                    org=institute.org,
                    fid=institute.fid,
                    bankid=bankid,
                )
                dtstart = date_since.replace(tzinfo=utils.UTC)
                dtend = date_until.replace(tzinfo=utils.UTC)
                s1 = StmtRq(
                    acctid=acctid,
                    dtstart=dtstart,
                    dtend=dtend,
                    accttype="CHECKING",
                )
                ofx = self.get_statements(client, password, s1)
                for account in ofx.accounts:
                    if not account.statement.transactions:
                        continue
                    for transaction in account.statement.transactions:
                        vals = self._prepare_ofx_transaction_line(transaction)
                        if vals:
                            lines.append(vals)
            except Exception as e:
                raise UserError(
                    _("The following problem occurred during import.\n\n %s") % str(e)
                ) from e
        return lines, {}

    @api.model
    def _prepare_ofx_transaction_line(self, transaction):
        payment_ref = transaction.payee
        if transaction.checknum:
            payment_ref += " " + transaction.checknum
        if transaction.memo:
            payment_ref += " : " + transaction.memo
        vals = {
            "date": transaction.date,
            "payment_ref": payment_ref,
            "amount": float(transaction.amount),
            "unique_import_id": transaction.id,
        }
        return vals

    def import_ofx_institutions(self):
        OfxInstitution = self.env["ofx.institution"]
        try:
            with requests.get(
                "http://www.ofxhome.com/api.php?all=yes", timeout=30
            ) as f:
                response = f.text
            institute_list = {
                fi.get("id").strip(): fi.get("name").strip()
                for fi in ET.fromstring(response)
            }
        except Exception as e:
            raise UserError(_(e)) from e

        for ofxhome_id, name in institute_list.items():
            institute = OfxInstitution.search([("ofxhome_id", "=", ofxhome_id)])
            vals = {
                "name": name,
                "ofxhome_id": ofxhome_id,
            }
            if institute:
                institute.write(vals)
            else:
                OfxInstitution.create(vals)

    def _create_or_update_statement(
        self, data, statement_date_since, statement_date_until
    ):
        # deleting blank statement for OFX online import
        res = super()._create_or_update_statement(
            data, statement_date_since, statement_date_until
        )
        if self.service == "OFX":
            unfiltered_lines, statement_values = data
            if not unfiltered_lines:
                unfiltered_lines = []
            if not statement_values:
                statement_values = {}
            statement_values["name"] = self.make_statement_name(statement_date_since)
            filtered_lines = self._get_statement_filtered_lines(
                unfiltered_lines,
                statement_values,
                statement_date_since,
                statement_date_until,
            )
            if not filtered_lines:
                return
            if filtered_lines:
                statement_values.update(
                    {"line_ids": [[0, False, line] for line in filtered_lines]}
                )
            self._update_statement_balances(statement_values)
            statement = self._statement_create_or_write(statement_values)
            self._journal_set_statement_source()
            if not statement.line_ids:
                statement.unlink()
        return res


class OFXInstitutionLine(models.Model):
    _name = "ofx.institution.line"
    _description = "OFX Institution Line"
    _rec_name = "institution_id"

    institution_id = fields.Many2one("ofx.institution", "Institution")
    username = fields.Char()
    password = fields.Char()
    bankid = fields.Char()
    provider_id = fields.Many2one("online.bank.statement.provider")
    account_id = fields.Char()
