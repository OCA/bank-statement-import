# Copyright 2022 AGEPoly
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import re

from lxml import etree

from odoo import _, models

SettlementCurrency = "SC"
OriginalCurrency = "OC"

ENDING_BALANCE_REASON = {
  '10' : "Negative balance of technical merchant account.",
  '20' : "Balance of technical merchant account is below minimum amount for settlement.",
  '30' : "Merchant settlement has been blocked by acquirer.",
  '40' : "Insufficient data for merchant settlement"
}

import logging
_logger = logging.getLogger(__name__)

class MRXParser(models.AbstractModel):
    _name = "account.statement.import.mrx.parser"
    _description = "Account Bank Statement Import merchantReconciliationXML (MRX) parser"

    def parse_int(self, ns, node, search_str):
        found_node = node.xpath(search_str)
        if found_node:
            if isinstance(found_node[0], str):
                return int(found_node[0])
            else:
                return int(found_node[0].text)
        return None

    def parse_float(self, ns, node, search_str):
        found_node = node.xpath(search_str)
        if found_node:
            if isinstance(found_node[0], str):
                return float(found_node[0])
            else:
                return float(found_node[0].text)
        return None

    def parse_text(self, ns, node, search_str):
        found_node = node.xpath(search_str)
        _logger.warning(found_node)
        if found_node:
            if isinstance(found_node[0], str):
                return found_node[0]
            else:
                return found_node[0].text
        return None

    def add_value_from_node(self, ns, node, xpath_str, obj, attr_name, join_str=None):
        """Add value to object from first or all nodes found with xpath.

        If xpath_str is a list (or iterable), it will be seen as a series
        of search path's in order of preference. The first item that results
        in a found node will be used to set a value."""
        if not isinstance(xpath_str, (list, tuple)):
            xpath_str = [xpath_str]
        for search_str in xpath_str:
            found_node = node.xpath(search_str)
            _logger.warning(found_node)
            if found_node:
                if isinstance(found_node[0], str):
                    attr_value = found_node[0]
                elif join_str is None:
                    attr_value = found_node[0].text
                else:
                    attr_value = join_str.join([x.text for x in found_node])
                obj[attr_name] = attr_value
                return
        obj[attr_name] = None


    def trxFromfAdj(self, ns, node, moreInfos={}):
        narration = moreInfos.copy()
        for tag in ["stlEntryType", "stlEntrySubType", "fAdjText", "passStlEntryNo", "fAdjDate"]:
            self.add_value_from_node(ns, node, ["./{}".format(tag)], narration, tag)
        trx = self.get_base_line()
        trx["narration"] = str(narration)        
        trx["ref"] = narration["fAdjText"]
        trx["payment_ref"] = narration["passStlEntryNo"]
        trx["unique_import_id"] =  "adj{}".format(trx["payment_ref"])
        trx["amount"] = self.parse_float(ns, node, "aFAdjNetSC")
        trx["date"] = narration["fAdjDate"]
        trx["transaction_type"] = "ADJ - {} - {}".format(narration["stlEntryType"], narration["stlEntrySubType"])
        return trx

    def get_base_line(self):
        return {"payment_ref": "/", "amount": 0}

    def parse_statement(self, ns, node):
        """Parse a single Stmt node."""
        result = {}
        transactions = []
        paymentMoreInfos = {}
        _logger.warning(node)

        self.add_value_from_node(
            ns, node, ["./passStlAcctNo"], paymentMoreInfos, "account_number",
        )
        self.add_value_from_node(
            ns, node, ["./iban"], paymentMoreInfos, "iban",
        )

        self.add_value_from_node(
            ns, node, ["./stlCurCode"], result, "currency"
        )

        payment = node.xpath("./payment")[0]

        self.add_value_from_node(
            ns, payment, ["./paymentNo"], result, "name"
        )

        maybe_opening_balance = payment.xpath("./openingBalance")
        if maybe_opening_balance:
            result["balance_start"] = self.parse_float(ns, maybe_opening_balance[0], "./aOpBalSC")
        else:
            result["balance_start"] = 0.0  # last payment was done correctly

        maybe_closing_balance = payment.xpath("./closingBalance")
        # prepare the payment line (maybe 0 for non payment)
        trx = self.get_base_line()
        if maybe_closing_balance:
            result["balance_end_real"], self.parse_float(ns, maybe_closing_balance[0], "./aClBalSC")

            self.add_value_from_node(ns, payment, ["./clBalReason"], paymentMoreInfos, "clBalReason")
            self.add_value_from_node(ns, payment, ["./clBalDate"], paymentMoreInfos, "clBalDate")
            result["clBalReasonText"] = ENDING_BALANCE_REASON.get(result["clBalReason"], _("Unknow Ending Balance Reason Code"))

            trx["ref"] = _("Non Payment from Wordline (SIX)")
            trx["date"] = paymentMoreInfos["clBalDate"]
            trx["amount"] = 0.0
            trx["transaction_type"] = "NONPAYMENT"

        else:

            result["balance_end_real"] = 0.0  # this payment

            for tag in ["paymentType", "paymentDate", "paymentNo", "valueDate"]:
                self.add_value_from_node(ns, payment, ["./{}".format(tag)], paymentMoreInfos, tag)

            trx["ref"] = _("Payment from Wordline (SIX)")
            trx["payment_ref"] = paymentMoreInfos["paymentNo"]
            trx["unique_import_id"] =  "pay{}".format(trx["payment_ref"])
            trx["date"] = paymentMoreInfos["valueDate"]
            trx["amount"] = -1 * self.parse_float(ns, payment, "./sum/sumSC/aPaymentSC")
            trx["account_number"] = paymentMoreInfos["iban"]
            trx["transaction_type"] = "PAYMENT"

        trx["narration"] = str(paymentMoreInfos)
        transactions.append(trx)

        for businessPart in payment:
            _logger.warning("bp")
            _logger.warning(businessPart)

            if businessPart.tag == "fAdj":
                    #adj_type = parse_int(ns, contract, "./stlEntryType")
                    #if adj_type == 46:
                    #    trx = self.get_base_line("Accumulated Rounding Difference")
                        #rounding_diff  = # LINE_CREATE
                    #else:
                transactions.append(self.trxFromfAdj(ns, businessPart, paymentMoreInfos))
                continue
            elif businessPart.tag != "businessPart":
                continue

            bpMoreInfos = paymentMoreInfos.copy()
            bpMoreInfos["passBusPartId"] = self.parse_text(ns, businessPart, './passBusPartId')

            for contract in businessPart:
                coMoreInfos = bpMoreInfos.copy()
                coMoreInfos["extVPNo"] = self.parse_text(ns, contract, './extVPNo')
                coMoreInfos["contractCategory"] = self.parse_text(ns, contract, './contractCategory')

                if contract.tag != "contract":
                    continue

                for entry in contract:
                    if entry.tag == "fAdj":
                        transactions.append(self.trxFromfAdj(ns, contract, coMoreInfos))
                        continue
                    elif entry.tag != "stlEntry":
                        continue

                    enMoreInfos = coMoreInfos.copy()
                    enMoreInfos["passStlEntryNo"] = self.parse_text(ns, entry, './sumSlip/passStlEntryNo')
                    enMoreInfos["origin"] = self.parse_text(ns, entry, './sumSlip/origin')
                    enMoreInfos["sumSlipId"] = self.parse_text(ns, entry, './sumSlip/sumSlipId')
                    enMoreInfos["trmId"] = self.parse_text(ns, entry, './sumSlip/trmId')
                    enMoreInfos["trmPer"] = self.parse_text(ns, entry, './sumSlip/trmPer')


                    for trx in entry.xpath("./sumSlip/trx"):
                        _logger.warning(trx)
                        trxMoreInfos = enMoreInfos.copy()
                        trxMoreInfos["trxType"] = self.parse_text(ns, trx, './trxType')
                        trxMoreInfos["trxTypeId"] = self.parse_text(ns, trx, './trxTypeId')
                        trxMoreInfos["trxIndicator"] = self.parse_text(ns, trx, './trxIndicator')
                        trxMoreInfos["pan"] = self.parse_text(ns, trx, './pan')
                        trxMoreInfos["authNo"] = self.parse_text(ns, trx, './authNo')
                        trxMoreInfos["refNo"] = self.parse_text(ns, trx, './refNo')
                        trxMoreInfos["trmTrxNo"] = self.parse_text(ns, trx, './trmTrxNo')
                        trxMoreInfos["addlMercData"] = self.parse_text(ns, trx, './addlMercData')
                        trxMoreInfos["addlStmntText"] = self.parse_text(ns, trx, './addlStmntText')
                        trxMoreInfos["arn"] = self.parse_text(ns, trx, './arn')
                        trxMoreInfos["dccInd"] = self.parse_text(ns, trx, './dccInd')
                        trxMoreInfos["isReversal"] = self.parse_text(ns, trx, './isReversal')
                        trxMoreInfos["entryType"] = self.parse_text(ns, trx, './entryType')
                        trxMoreInfos["accountIndex"] = self.parse_text(ns, trx, './accountIndex')
                        trxMoreInfos["cardProduct"] = self.parse_text(ns, trx, './cardProduct')
                        trxMoreInfos["unBlendCat"] = self.parse_text(ns, trx, './unBlendCat')
    
                        amount = self.parse_float(ns, trx, "./aTrxGrosSC")
                        amount_currency = self.parse_float(ns, trx, "./aTrxOC")
                        foreign_currency = self.parse_text(ns, trx, "./aTrxOC/@c")
                        _logger.warning(foreign_currency)
                        _logger.warning(self.env['res.currency'].search([['name', 'ilike', foreign_currency]]))
    
                        parsed_foreign_currency = (self.env['res.currency'].search([['name', 'ilike', foreign_currency]]).mapped('id') or [None])[0]
    
                        amount_comm = self.parse_float(ns, trx, "./aComEffSC")
    
                        complete_date = "{}-{}".format(self.parse_text(ns, trx, "./trxDate"), self.parse_text(ns, trx, "./trxTime"))
    
                        trxMoreInfos["grossAmount"] = amount
                        trxMoreInfos["commAmount"] = amount_comm
                        trxMoreInfos["netAmount"] = self.parse_float(ns, trx, "./aNetSC")
    
                        grossTrx = self.get_base_line()
                        grossTrx["ref"] = self.parse_text(ns, trx, "./addlStmntText") or _("Transaction")
                        grossTrx["payment_ref"] = self.parse_text(ns, trx, "./passTrxId")
                        grossTrx["unique_import_id"] =  "trx{}".format(grossTrx["payment_ref"])
                        grossTrx["amount"] = amount
                        grossTrx["transaction_type"] = trxMoreInfos["trxType"]
                        if foreign_currency != result["currency"]:
                            grossTrx["amount_currency"] = amount_currency
                            grossTrx["foreign_currency_id"] = parsed_foreign_currency
                        grossTrx["date"] = complete_date
                        grossTrx["narration"] = str(trxMoreInfos) 
    
                        trxMoreInfos["isComm"] = True
    
                        commTrx = self.get_base_line()
                        commTrx["ref"] = _("Commission on transaction")
                        commTrx["payment_ref"] = self.parse_text(ns, trx, "./passTrxId")
                        commTrx["unique_import_id"] =  "comm{}".format(commTrx["payment_ref"])
                        commTrx["amount"] = amount_comm
                        commTrx["transaction_type"] = "COMM-{}".format(trxMoreInfos["trxType"])
                        commTrx["date"] = complete_date
                        commTrx["narration"] = str(trxMoreInfos)
    
                        transactions.append(grossTrx)
                        transactions.append(commTrx)

        result["transactions"] = transactions
        result["date"] = None
        if transactions:
            result["date"] = sorted(
                transactions, key=lambda x: x["date"], reverse=True
            )[0]["date"]
        return result

    def parse(self, data):
        """Parse a camt.052 or camt.053 or camt.054 file."""
        try:
            root = etree.fromstring(data, parser=etree.XMLParser(recover=True))
        except etree.XMLSyntaxError:
            try:
                # ABNAmro is known to mix up encodings
                root = etree.fromstring(data.decode("iso-8859-15").encode("utf-8"))
            except etree.XMLSyntaxError:
                root = None
        _logger.warning("aa")

        _logger.warning(root)

        if root is None:
            raise ValueError("Not a valid xml file, or not an xml file at all.")

        ns = ""
        stlAccounts = root.xpath("./reportingPart/settlingPart/stlAccount")
        _logger.warning(stlAccounts)

        if not stlAccounts:
            raise ValueError("Not a valid mrx xml file.")

        statements = []
        currency = None
        account_number = None

        for stlAccount in stlAccounts:
                statement = self.parse_statement(ns, stlAccount)
                if len(statement["transactions"]):
                    if "currency" in statement:
                        currency = statement.pop("currency")
                    if "account_number" in statement:
                        account_number = statement.pop("account_number")
                    statements.append(statement)
        return currency, account_number, statements
