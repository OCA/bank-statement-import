# -*- coding: utf-8 -*-
"""Class to parse camt files."""
# © 2013-2016 Therp BV <http://therp.nl>
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re
from lxml import etree

from odoo import models


class CamtParser(models.AbstractModel):
    _name = 'account.bank.statement.import.camt.parser'
    """Parser for camt bank statement import files."""

    def parse_amount(self, ns, node):
        """Parse element that contains Amount and CreditDebitIndicator."""
        if node is None:
            return 0.0
        sign = 1
        amount = 0.0
        sign_node = node.xpath('ns:CdtDbtInd', namespaces={'ns': ns})
        if not sign_node:
            sign_node = node.xpath(
                '../../ns:CdtDbtInd', namespaces={'ns': ns})
        if sign_node and sign_node[0].text == 'DBIT':
            sign = -1
        amount_node = node.xpath('ns:Amt', namespaces={'ns': ns})
        if not amount_node:
            amount_node = node.xpath(
                './ns:AmtDtls/ns:TxAmt/ns:Amt', namespaces={'ns': ns})
        if amount_node:
            amount = sign * float(amount_node[0].text)
        return amount

    def add_value_from_node(
            self, ns, node, xpath_str, obj, attr_name, join_str=None):
        """Add value to object from first or all nodes found with xpath.

        If xpath_str is a list (or iterable), it will be seen as a series
        of search path's in order of preference. The first item that results
        in a found node will be used to set a value."""
        if not isinstance(xpath_str, (list, tuple)):
            xpath_str = [xpath_str]
        for search_str in xpath_str:
            found_node = node.xpath(search_str, namespaces={'ns': ns})
            if found_node:
                if join_str is None:
                    attr_value = found_node[0].text
                else:
                    attr_value = join_str.join([x.text for x in found_node])
                obj[attr_name] = attr_value
                break

    def parse_transaction_details(self, ns, node, transaction):
        """Parse TxDtls node."""
        # message
        self.add_value_from_node(
            ns, node, [
                './ns:RmtInf/ns:Ustrd|./ns:RtrInf/ns:AddtlInf',
                './ns:AddtlNtryInf',
                './ns:Refs/ns:InstrId',
            ], transaction, 'name', join_str='\n')
        # name
        self.add_value_from_node(
            ns, node, [
                './ns:AddtlTxInf',
            ], transaction, 'note', join_str='\n')
        # eref
        self.add_value_from_node(
            ns, node, [
                './ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref',
                './ns:Refs/ns:EndToEndId',
                './ns:Ntry/ns:AcctSvcrRef'
            ],
            transaction, 'ref'
        )
        amount = self.parse_amount(ns, node)
        if amount != 0.0:
            transaction['amount'] = amount
        # remote party values
        party_type = 'Dbtr'
        party_type_node = node.xpath(
            '../../ns:CdtDbtInd', namespaces={'ns': ns})
        if party_type_node and party_type_node[0].text != 'CRDT':
            party_type = 'Cdtr'
        party_node = node.xpath(
            './ns:RltdPties/ns:%s' % party_type, namespaces={'ns': ns})
        if party_node:
            self.add_value_from_node(
                ns, party_node[0], './ns:Nm', transaction, 'partner_name')
        # Get remote_account from iban or from domestic account:
        account_node = node.xpath(
            './ns:RltdPties/ns:%sAcct/ns:Id' % party_type,
            namespaces={'ns': ns}
        )
        if account_node:
            iban_node = account_node[0].xpath(
                './ns:IBAN', namespaces={'ns': ns})
            if iban_node:
                transaction['account_number'] = iban_node[0].text
            else:
                self.add_value_from_node(
                    ns, account_node[0], './ns:Othr/ns:Id', transaction,
                    'account_number'
                )

    def parse_entry(self, ns, node, transaction=None):
        """Parse an Ntry node and yield transactions"""
        if transaction is None:
            transaction = {'name': '/', 'amount': 0}  # fallback defaults
        self.add_value_from_node(
            ns, node, './ns:BookgDt/ns:Dt', transaction, 'date')
        amount = self.parse_amount(ns, node)
        if amount != 0.0:
            transaction['amount'] = amount
        self.add_value_from_node(
            ns, node, './ns:AddtlNtryInf', transaction, 'name')
        self.add_value_from_node(
            ns, node, [
                './ns:NtryDtls/ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref',
                './ns:NtryDtls/ns:Btch/ns:PmtInfId',
                './ns:NtryDtls/ns:TxDtls/ns:Refs/ns:AcctSvcrRef'
            ],
            transaction, 'ref'
        )

        details_nodes = node.xpath(
            './ns:NtryDtls/ns:TxDtls', namespaces={'ns': ns})
        if len(details_nodes) == 0:
            yield transaction
            return
        transaction_base = transaction
        for node in details_nodes:
            transaction = transaction_base.copy()
            self.parse_transaction_details(ns, node, transaction)
            yield transaction

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
                    start_balance_node = balance_node[0]
                elif node_name == 'CLBD':
                    end_balance_node = balance_node[0]
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
        result = {}
        self.add_value_from_node(
            ns, node, [
                './ns:Acct/ns:Id/ns:IBAN',
                './ns:Acct/ns:Id/ns:Othr/ns:Id',
            ], result, 'account_number'
        )
        self.add_value_from_node(
            ns, node, './ns:Id', result, 'name')
        self.add_value_from_node(
            ns, node, './ns:Acct/ns:Ccy', result, 'currency')
        result['balance_start'], result['balance_end_real'] = (
            self.get_balance_amounts(ns, node))
        entry_nodes = node.xpath('./ns:Ntry', namespaces={'ns': ns})
        transactions = []
        for entry_node in entry_nodes:
            transactions.extend(self.parse_entry(ns, entry_node))
        result['transactions'] = transactions
        result['date'] = None
        if transactions:
            result['date'] = sorted(transactions,
                                    key=lambda x: x['date'],
                                    reverse=True
                                    )[0]['date']
        return result

    def check_version(self, ns, root):
        """Validate validity of camt file."""
        # Check wether it is camt at all:
        re_camt = re.compile(
            r'(^urn:iso:std:iso:20022:tech:xsd:camt.'
            r'|^ISO:camt.)'
        )
        if not re_camt.search(ns):
            raise ValueError('no camt: ' + ns)
        # Check wether version 052 ,053 or 054:
        re_camt_version = re.compile(
            r'(^urn:iso:std:iso:20022:tech:xsd:camt.054.'
            r'|^urn:iso:std:iso:20022:tech:xsd:camt.053.'
            r'|^urn:iso:std:iso:20022:tech:xsd:camt.052.'
            r'|^ISO:camt.054.'
            r'|^ISO:camt.053.'
            r'|^ISO:camt.052.)'
        )
        if not re_camt_version.search(ns):
            raise ValueError('no camt 052 or 053 or 054: ' + ns)
        # Check GrpHdr element:
        root_0_0 = root[0][0].tag[len(ns) + 2:]  # strip namespace
        if root_0_0 != 'GrpHdr':
            raise ValueError('expected GrpHdr, got: ' + root_0_0)

    def parse(self, data):
        """Parse a camt.052 or camt.053 or camt.054 file."""
        try:
            root = etree.fromstring(
                data, parser=etree.XMLParser(recover=True))
        except etree.XMLSyntaxError:
            # ABNAmro is known to mix up encodings
            root = etree.fromstring(
                data.decode('iso-8859-15').encode('utf-8'))
        if root is None:
            raise ValueError(
                'Not a valid xml file, or not an xml file at all.')
        ns = root.tag[1:root.tag.index("}")]
        self.check_version(ns, root)
        statements = []
        currency = None
        account_number = None
        for node in root[0][1:]:
            statement = self.parse_statement(ns, node)
            if len(statement['transactions']):
                if 'currency' in statement:
                    currency = statement.pop('currency')
                if 'account_number' in statement:
                    account_number = statement.pop('account_number')
                statements.append(statement)
        return currency, account_number, statements
