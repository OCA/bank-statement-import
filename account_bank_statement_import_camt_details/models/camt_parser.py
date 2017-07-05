# -*- coding: utf-8 -*-
# © 2017 Compassion CH <http://www.compassion.ch>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models
from odoo.tools import OrderedDict


class CamtDetailsParser(models.AbstractModel):
    """Parser for camt bank statement import files."""
    _inherit = 'account.bank.statement.import.camt.parser'

    def parse_transaction_details(self, ns, node, transaction):
        """Parse transaction details (message, party, account...)."""
        super(CamtDetailsParser, self).parse_transaction_details(
            ns, node, transaction)

        # remote party values
        party_type = 'Dbtr'
        party_type_node = node.xpath(
            '../../ns:CdtDbtInd', namespaces={'ns': ns})
        if party_type_node and party_type_node[0].text != 'CRDT':
            party_type = 'Cdtr'
        address_node = node.xpath(
            './ns:RltdPties/ns:%s/ns:PstlAdr' % party_type,
            namespaces={'ns': ns})
        if address_node and not transaction.get('partner_address'):
            address_values = OrderedDict()
            street_node = address_node[0].xpath(
                './ns:StrtNm', namespaces={'ns': ns})
            if street_node:
                address_values['street'] = street_node[0].text
            building_node = address_node[0].xpath(
                './ns:BldgNb', namespaces={'ns': ns})
            if building_node:
                address_values['building'] = building_node[0].text
            zip_node = address_node[0].xpath(
                './ns:PstCd', namespaces={'ns': ns})
            if zip_node:
                address_values['zip'] = zip_node[0].text
            city_node = address_node[0].xpath(
                './ns:TwnNm', namespaces={'ns': ns})
            if city_node:
                address_values['city'] = city_node[0].text
            transaction['partner_address'] = self._format_partner_address(
                address_values)

        # BIC node
        bic_node = node.xpath(
            './ns:RltdAgts/ns:%sAgt/ns:FinInstnId/ns:BIC' % party_type,
            namespaces={'ns': ns})
        if bic_node:
            transaction['partner_bic'] = bic_node[0].text

        # Transfer account info in fields
        transaction['partner_account'] = transaction.get('account_number')

    def _format_partner_address(self, address_values):
        """
        Hook for formatting the partner address read in CAMT bank statement.
        :param address_values: dict: all address values found in statement
            Possible keys are ['street', 'building', 'zip', 'city']
            Not all keys may be present.
        :return: str: formatted address
        """
        return ', '.join(address_values.values())
