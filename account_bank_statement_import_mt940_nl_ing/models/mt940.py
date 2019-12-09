# Copyright (C) 2014-2015 Therp BV <http://therp.nl>.
# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MT940Parser(models.AbstractModel):
    _inherit = 'account.bank.statement.import.mt940.parser'

    def get_header_lines(self):
        if self.get_mt940_type() == 'mt940_nl_ing':
            return 0
        return super(MT940Parser, self).get_header_lines()

    def get_header_regex(self):
        if self.get_mt940_type() == 'mt940_nl_ing':
            return '^0000 01INGBNL2AXXXX|^{1'
        return super(MT940Parser, self).get_header_regex()

    def get_footer_regex(self):
        if self.get_mt940_type() == 'mt940_nl_ing':
            return '^-}$|^-XXX$'
        return super(MT940Parser, self).get_footer_regex()

    def get_tag_regex(self):
        if self.get_mt940_type() == 'mt940_nl_ing':
            return '^:[0-9]{2}[A-Z]*:'
        return super(MT940Parser, self).get_tag_regex()

    def get_codewords(self):
        if self.get_mt940_type() == 'mt940_nl_ing':
            return ['RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF', 'EREF',
                    'PREF', 'REMI', 'ID', 'PURP', 'ULTB', 'ULTD', 'CREF',
                    'IREF', 'CNTP', 'ULTC', 'EXCH', 'CHGS']
        return super(MT940Parser, self).get_codewords()
