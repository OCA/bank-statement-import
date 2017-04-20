# -*- coding: utf-8 -*-
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models


class CamtReftypeParser(models.AbstractModel):
    """Parser for camt bank statement import files."""
    _inherit = 'account.bank.statement.import.camt.parser'

    def parse_transaction_details(self, ns, node, transaction):
        super(CamtReftypeParser, self).parse_transaction_details(
            ns, node, transaction)

        self.add_value_from_node(
            ns, node, [
                './ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Tp/ns:CdOrPrtry/'
                'ns:Prtry',
            ],
            transaction, 'camt_ref_type'
        )
