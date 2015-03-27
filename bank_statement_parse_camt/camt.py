# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Copyright (C) 2013-2015 Therp BV <http://therp.nl>
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
from lxml import etree
from openerp.addons.bank_statement_parse.parserlib import (
    BankStatement,
    BankTransaction
)
from openerp.tools.translate import _


class CamtParser(object):
    """Parser for camt bank statement import files."""

    def parse_amount(self, ns, node):
        """Parse element that contains Amount and CreditDebitIndicator."""
        if not node:
            return 0.0
        sign = -1 if node.find(ns + 'CdtDbtInd').text == 'DBIT' else 1
        return sign * float(node.find(ns + 'Amt').text)

    def add_value_from_node(
            self, ns, node, xpath_str, obj, attr_name, join_str=None):
        """Add value to object from first or all nodes found with xpath."""
        found_node = node.xpath(xpath_str, namespaces={'ns': ns})
        if found_node:
            if join_str == None:
                attr_value = found_node[0].text
            else:
                attr_value = join_str.join([x.text for x in found_node])
            setattr(obj, attr_name, attr_value)

    def get_party_values(self, ns, details_node, transaction):
        """
        Determine to get either the debtor or creditor party node
        and extract the available data from it
        """
        party_type = 'Dbtr'
        party_type_node = details_node.xpath(
            '../../ns:CdtDbtInd', namespaces={'ns': ns})
        if party_type_node and party_type_node[0].text != 'CRDT':
            party_type = 'Cdtr'
        party_node = details_node.xpath(
            './ns:RltdPties/ns:%s' % party_type, namespaces={'ns': ns})
        if party_node:
            self.add_value_from_node(
                ns, party_node, './ns:Nm', transaction, 'remote_owner')
            self.add_value_from_node(
                ns, party_node, './ns:PstlAdr/ns:Ctry', transaction,
                'remote_owner_country'
            )
            address_node = party_node.xpath(
                './ns:PstlAdr/ns:AdrLine', namespaces={'ns': ns})
            if address_node:
                transaction.remote_owner_address = [address_node[0].text]
        account_node = details_node.xpath(
            './ns:RltdPties/ns:%sAcct/ns:Id' % party_type,
            namespaces={'ns': ns}
        )
        # Get remote_account from iban or from domestic account:
        if account_node:
            iban_node = account_node[0].xpath(
                './ns:IBAN', namespaces={'ns': ns})
            if iban_node:
                transaction.remote_account = iban_node[0].text
                bic_node = details_node.xpath(
                    './ns:RltdAgts/ns:%sAgt/ns:FinInstnId/ns:BIC' % party_type,
                    namespaces={'ns': ns}
                )
                if bic_node:
                    transaction.remote_bank_bic = bic_node[0].text
            else:
                self.add_value_from_node(
                    ns, account_node, './ns:Othr/ns:Id', transaction,
                    'remote_account'
                )

    def parse_entry(self, ns, node):
        """Parse transaction (entry) node."""
        transaction = BankTransaction()
        for attr_name, xpath_str in {
                'transfer_type': './ns:BkTxCd/ns:Prtry/ns:Cd',
                'execution_date': './ns:BookgDt/ns:Dt',
                'value_date': './ns:ValDt/ns:Dt',
            }.items():
            self.add_value_from_node(
                ns, node, xpath_str, transaction, attr_name)
        transaction.transferred_amount = self.parse_amount(ns, node)
        details_node = node.xpath(
            './ns:NtryDtls/ns:TxDtls', namespaces={'ns': ns})
        if details_node:
            # message
            self.add_value_from_node(
                ns, details_node, './ns:RmtInf/ns:Ustrd', transaction,
                'message', join_str=' '
            )
            # reference
            self.add_value_from_node(
                ns, details_node, './ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref',
                transaction, 'reference'
            )
            if not transaction.reference:
                self.add_value_from_node(
                    ns, details_node, './ns:Refs/ns:EndToEndId',
                    transaction, 'reference'
                )
            # remote party values
            self.get_party_values(ns, details_node, transaction)
        # If no message, try to get it from additional entry info
        if not transaction.message:
            self.add_value_from_node(
                ns, node, './ns:AddtlNtryInf', transaction, 'message')
        transaction.data = etree.tostring(node)
        return transaction

    def get_balance_amounts(self, ns, node):
        """Return opening and closing balance.

        Depending on kind of balance and statement, the balance might be in a
        different kind of node:
        OPBD = OpeningBalance
        PRCD = PreviousClosingBalance
        ITBD = InterimBalance (first ITBD is start-, second is end-balance)
        CLBD = ClosingBalance
        """
        start_balance_node = None
        end_balance_node = None
        for node_name in ['OPBD', 'PRCD', 'CLBD', 'ITBD']:
            code_expr = (
                './ns:Bal/ns:Tp/ns:CdOrPrtry/ns:Cd[text()="%s"]/../../..' %
                node_name
            )
            balance_node = node.xpath(code_expr, namespaces={'ns': ns})
            if balance_node:
                if node_name in ['OPBD', 'PRCD']:
                    start_balance_node = balance_node
                elif node_name == 'CLBD':
                    end_balance_node = balance_node
                else:
                    if not start_balance_node:
                        start_balance_node = balance_node[0]
                    if not end_balance_node:
                        end_balance_node = balance_node[-1]
        return (
            self.parse_amount(ns, start_balance_node),
            self.parse_amount(ns, end_balance_node)
        )

    def parse_statement(self, ns, node):
        """Parse a single Stmt node."""
        statement = BankStatement()
        # local_account
        local_account_node = node.xpath(
            './ns:Acct/ns:Id/ns:IBAN', namespaces={'ns': ns})
        if not local_account_node:
            local_account_node = node.xpath(
                './ns:Acct/ns:Id/ns:Othr/ns:Id', namespaces={'ns': ns})
        statement.local_account = (
            local_account_node and local_account_node[0].text)
        # statement_id
        statement_id_node = node.xpath(
            './ns:Stmt/ns:Id', namespaces={'ns': ns})
        if not statement_id_node:
            statement_id_node = node.xpath(
                './ns:Rpt/ns:Id', namespaces={'ns': ns})
        statement.statement_id = (
            statement_id_node and statement_id_node[0].text)
        # local_currency
        local_currency_node = node.xpath(
            './ns:Acct/ns:Ccy', namespaces={'ns': ns})
        statement.local_currency = (
            local_currency_node and local_currency_node[0].text)
        # Start and end balance
        (statement.start_balance, statement.end_balance) = (
            self.get_balance_amounts(ns, node))
        transaction_nodes = node.xpath('./ns:Ntry', namespaces={'ns': ns})
        for entry_node in transaction_nodes:
            transaction = self.parse_entry(ns, entry_node)
            statement.transactions.append(transaction)
        if statement.transactions:
            # Take the statement date from the first transaction
            statement.date = datetime.strptime(
                statement.transactions[0]['execution_date'], "%Y-%m-%d")
        return statement

    def check_version(self, ns, root):
        """
        Validate validity of camt file.
        """
        # Check wether it is camt at all:
        if (not ns.startswith(
                '{urn:iso:std:iso:20022:tech:xsd:camt.')
                and not ns.startswith('{ISO:camt.')):
            raise ValueError(_(
                "This does not seem to be a CAMT format bank statement."))
        # Check wether version 052 or 053:
        if (not ns.startswith(
                '{urn:iso:std:iso:20022:tech:xsd:camt.053.')
                and not ns.startswith('{ISO:camt.053')
                and not ns.startswith(
                    '{urn:iso:std:iso:20022:tech:xsd:camt.052.')
                and not ns.startswith('{ISO:camt.052')):
            raise ValueError(_(
                "Only camt.052 and camt.053 supported at the moment."))
        # Check GrpHdr element:
        root_0_0 = root[0][0].tag[len(ns):]  # root tag stripped of namespace
        if root_0_0 != 'GrpHdr':
            raise ValueError(_(
                "Expected tag '%s', got '%s' instead." %
                ('GrpHdr', root_0_0)
            ))

    def parse(self, data):
        """Parse a camt.052 or camt.053 file."""
        try:
            root = etree.fromstring(
                data, parser=etree.XMLParser(recover=True))
        except etree.XMLSyntaxError:
            # ABNAmro is known to mix up encodings
            root = etree.fromstring(
                data.decode('iso-8859-15').encode('utf-8'))
        if not root:
            raise ValueError(_(
                "Not a valid xml file, or not an xml file at all."))
        ns = root.tag[1:root.tag.index("}") + 1]
        self.check_version(ns, root)
        statements = []
        for node in root[0][1:]:
            statement = self.parse_statement(ns, node)
            if len(statement.transactions):
                statements.append(statement)
        return statements

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
