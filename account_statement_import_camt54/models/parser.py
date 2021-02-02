# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, exceptions, models


class CamtParser(models.AbstractModel):
    """Parser for camt bank statement import files."""

    _inherit = "account.statement.import.camt.parser"

    def _get_partner_ref(self, isr):
        ICP = self.env["ir.config_parameter"]
        ref_format = ICP.sudo().get_param("isr_partner_ref")
        if not ref_format:
            return
        config = ref_format.split(",")
        if len(config) == 2:
            start, size = config
        elif len(config) == 1:
            start = config[0]
            size = 6
        else:
            raise exceptions.UserError(
                _(
                    "Config parameter `isr_partner_ref` is wrong.\n"
                    "It must be in format `i[,n]` \n"
                    "where `i` is the position of the first digit and\n"
                    "`n` the number of digit in the reference,"
                    " by default 6.\n"
                    'e.g. "13,6"'
                )
            )
        try:
            start = int(start) - 1  # count from 1 instead of 0
            size = int(size)
            end = start + size
        except ValueError:
            raise exceptions.UserError(
                _(
                    "Config parameter `isr_partner_ref` is wrong.\n"
                    "It must be in format `i[,n]` \n"
                    "`i` and `n` must be integers.\n"
                    'e.g. "13,6"'
                )
            )
        return isr[start:end].lstrip("0")

    def parse_transaction_details(self, ns, node, transaction):
        """Put ESR in label and add aditional information to label
        if no esr is available
        """
        super().parse_transaction_details(ns, node, transaction)
        # put the esr in the label. odoo reconciles based on the label,
        # if there is no esr it tries to use the information textfield

        isr_number = node.xpath(
            "./ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref", namespaces={"ns": ns}
        )
        if len(isr_number):
            transaction["payment_ref"] = isr_number[0].text
            partner_ref = self._get_partner_ref(isr_number[0].text)
            if partner_ref:
                transaction["partner_ref"] = partner_ref
        else:
            xpath_exprs = [
                "./ns:RmtInf/ns:Ustrd|./ns:RtrInf/ns:AddtlInf",
                "./ns:AddtlNtryInf",
                "/ns:Refs/ns:InstrId",
            ]
            payment_ref = transaction["payment_ref"]
            for xpath_expr in xpath_exprs:
                found_node = node.xpath(xpath_expr, namespaces={"ns": ns})
                if found_node:
                    payment_ref = found_node[0].text
                    break
            trans_id_node = (
                node.getparent()
                .getparent()
                .xpath("./ns:AcctSvcrRef", namespaces={"ns": ns})
            )
            if trans_id_node:
                payment_ref = "{} ({})".format(payment_ref, trans_id_node[0].text)
            if payment_ref:
                transaction["payment_ref"] = payment_ref
        # End add esr to the label.

        # add transaction id to ref
        self.add_value_from_node(
            ns,
            node,
            [
                "./../../ns:AcctSvcrRef",
                "./ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref",
                "./ns:Refs/ns:EndToEndId",
            ],
            transaction,
            "ref",
        )
        return True
