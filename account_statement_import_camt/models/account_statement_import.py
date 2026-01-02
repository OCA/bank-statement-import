# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import logging
import zipfile
from io import BytesIO

from odoo import models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        try:
            parser = self.env["account.statement.import.camt.parser"]
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            try:
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        currency, account_number, new = self._parse_file(
                            data.open(member).read()
                        )
                        transactions.extend(new)
                return currency, account_number, transactions
            # pylint: disable=except-pass
            except (zipfile.BadZipFile, ValueError):
                _logger.exception("BadZipfile exception")
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.", exc_info=True)
        return super()._parse_file(data_file)

    def _import_file(self):
        """
        inherit from AccountStatementImport to allow importing multiple statement files
        from different bank accounts
        """
        file_data = base64.b64decode(self.statement_file)

        try:
            with zipfile.ZipFile(BytesIO(file_data)) as zip_file:
                global_result = {
                    "statement_ids": [],
                    "notifications": [],
                }
                # browse files in zip
                for member in zip_file.namelist():
                    if member.lower().endswith((".xml", ".camt")):
                        try:
                            xml_content = zip_file.open(member).read()

                            # Create temporary xml file
                            attachment = self.env["ir.attachment"].create(
                                {
                                    "name": member,
                                    "datas": base64.b64encode(xml_content),
                                    "res_model": self._name,
                                    "res_id": self.id,
                                }
                            )
                            temp_result = {
                                "statement_ids": [],
                                "notifications": [],
                            }
                            self.with_context(
                                attachment_id=attachment.id
                            ).import_single_file(xml_content, temp_result)
                            for statement_id in temp_result["statement_ids"]:
                                statement = self.env["account.bank.statement"].browse(
                                    statement_id
                                )
                                statement.write(
                                    {"attachment_ids": [(4, attachment.id)]}
                                )

                            # merge results
                            global_result["statement_ids"].extend(
                                temp_result["statement_ids"]
                            )
                            global_result["notifications"].extend(
                                temp_result["notifications"]
                            )
                        except Exception as e:
                            _logger.exception(
                                f"Error processing file {member} in ZIP: {e}"
                            )
                            global_result["notifications"].append(
                                f"Error processing file {member} in ZIP: {e}"
                            )
                return global_result

        except zipfile.BadZipFile:
            pass
        return super()._import_file()
