# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import UserError
from odoo.tests import common


class TestGetPartnerRef(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.Parser = self.env["account.statement.import.camt.parser"]
        self.ICP = self.env["ir.config_parameter"]

    def test_no_ICP(self):
        """Test no partner ref is read if param is not set"""
        ref = "11 11111 11111 11111 11111 11111".replace(" ", "")
        partner_ref = self.Parser._get_partner_ref(ref)
        self.assertFalse(partner_ref)

    def test_ICP_empty(self):
        self.ICP.set_param("isr_partner_ref", "")
        ref = "11 11111 11111 11111 11111 11111".replace(" ", "")
        partner_ref = self.Parser._get_partner_ref(ref)
        self.assertFalse(partner_ref)

    def test_ICP_no_len(self):
        """Test a default len of 6 is set if not provided"""
        self.ICP.set_param("isr_partner_ref", "12")
        ref = "11 11111 11112 34567 11111 11111".replace(" ", "")
        partner_ref = self.Parser._get_partner_ref(ref)
        self.assertEqual(partner_ref, "234567")

    def test_ICP_full(self):
        """Test full format of partner ref definition"""
        self.ICP.set_param("isr_partner_ref", "12,6")
        ref = "11 11111 11112 34567 11111 11111".replace(" ", "")
        partner_ref = self.Parser._get_partner_ref(ref)
        self.assertEqual(partner_ref, "234567")

    def test_zero_stripped(self):
        """Test full format of partner ref definition"""
        self.ICP.set_param("isr_partner_ref", "12,6")
        ref = "11 11111 11110 00560 11111 11111".replace(" ", "")
        partner_ref = self.Parser._get_partner_ref(ref)
        self.assertEqual(partner_ref, "560")

    def test_bad_ICP(self):
        """Test ir config parameter validation"""
        self.ICP.set_param("isr_partner_ref", "")
        ref = "11 11111 11111 11111 11111 11111".replace(" ", "")

        self.ICP.set_param("isr_partner_ref", "A")
        with self.assertRaises(UserError):
            self.Parser._get_partner_ref(ref)

        self.ICP.set_param("isr_partner_ref", "A,B")
        with self.assertRaises(UserError):
            self.Parser._get_partner_ref(ref)

        self.ICP.set_param("isr_partner_ref", "1,X")
        with self.assertRaises(UserError):
            self.Parser._get_partner_ref(ref)

        self.ICP.set_param("isr_partner_ref", "A,8")
        with self.assertRaises(UserError):
            self.Parser._get_partner_ref(ref)
