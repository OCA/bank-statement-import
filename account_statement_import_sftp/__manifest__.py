# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bank Statement SFTP import",
    "summary": "Import bank statement from an SFTP server",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Odoo Community Association (OCA), Compassion CH",
    "maintainers": ["OCA"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "edi_storage_oca",  # OCA/edi
        "storage_backend_sftp",  # OCA/storage
        "account_statement_import",
        "base_automation",
    ],
    "data": [
        "data/edi_data.xml",
    ],
}
