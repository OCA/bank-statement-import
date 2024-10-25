# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import _, api, fields, models


class AccountStatementLineCreate(models.TransientModel):
    _name = "account.statement.line.create"
    _description = "Wizard to create statement lines"

    statement_id = fields.Many2one("account.bank.statement", string="Bank Statement")
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner Related",
        domain=["|", ("parent_id", "=", False), ("is_company", "=", True)],
    )
    journal_ids = fields.Many2many("account.journal", string="Journals Filter")
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
    )
    allow_blocked = fields.Boolean(string="Allow Litigation Move Lines")
    invoice = fields.Boolean(string="Linked to an Invoice or Refund")
    date_type = fields.Selection(
        [("due", "Due Date"), ("move", "Move Date")],
        string="Type of Date Filter",
        required=True,
    )
    due_date = fields.Date(default=fields.Date.context_today)
    move_date = fields.Date(default=fields.Date.context_today)
    move_line_ids = fields.Many2many("account.move.line", string="Move Lines")

    def default_get(self, field_list):
        res = super().default_get(field_list)
        res.update(
            {
                "target_move": "posted",
                "date_type": "due",
                "invoice": True,
            }
        )
        active_model = self.env.context.get("active_model")
        if active_model == "account.bank.statement":
            statement = (
                self.env[active_model]
                .browse(self.env.context.get("active_id"))
                .exists()
            )
            if statement:
                res.update(
                    {
                        "statement_id": statement.id,
                    }
                )
        return res

    def _prepare_move_line_domain(self):
        self.ensure_one()
        domain = [
            ("reconciled", "=", False),
            (
                "account_id.account_type",
                "in",
                ("asset_receivable", "liability_payable"),
            ),
            ("company_id", "=", self.env.company.id),
        ]
        if self.journal_ids:
            domain += [("journal_id", "in", self.journal_ids.ids)]
        else:
            journals = self.env["account.journal"].search([])
            domain += [("journal_id", "in", journals.ids)]
        if self.partner_id:
            domain += [("partner_id", "=", self.partner_id.id)]
        if self.target_move == "posted":
            domain += [("move_id.state", "=", "posted")]
        if not self.allow_blocked:
            domain += [("blocked", "!=", True)]
        if self.date_type == "due":
            domain += [
                "|",
                ("date_maturity", "<=", self.due_date),
                ("date_maturity", "=", False),
            ]
        elif self.date_type == "move":
            domain.append(("date", "<=", self.move_date))
        if self.invoice:
            domain.append(("move_id", "!=", False))
        paylines = self.env["account.payment"].search(
            [
                ("state", "in", ("draft", "posted", "sent")),
                ("line_ids", "!=", False),
            ]
        )
        if paylines:
            move_in_payment_ids = paylines.mapped("line_ids.id")
            domain += [("id", "not in", move_in_payment_ids)]
        return domain

    def populate(self):
        domain = self._prepare_move_line_domain()
        lines = self.env["account.move.line"].search(domain)
        self.move_line_ids = False
        self.move_line_ids = lines
        action = {
            "name": _("Select Move Lines to Create Statement"),
            "type": "ir.actions.act_window",
            "res_model": "account.statement.line.create",
            "view_mode": "form",
            "target": "new",
            "res_id": self.id,
            "context": self._context,
        }
        return action

    @api.onchange(
        "date_type",
        "move_date",
        "due_date",
        "journal_ids",
        "invoice",
        "target_move",
        "allow_blocked",
        "partner_id",
    )
    def move_line_filters_change(self):
        domain = self._prepare_move_line_domain()
        res = {"domain": {"move_line_ids": domain}}
        return res

    def create_statement_lines(self):
        if self.move_line_ids:
            active_model = self.env.context.get("active_model")
            if active_model == "account.journal":
                journal = self.env["account.journal"].browse(
                    self.env.context.get("active_id")
                )
                statement = self.env["account.bank.statement"].create(
                    {
                        "date": fields.Date.today(),
                        "name": _("%(journal_code)s Statement %(date)s")
                        % {
                            "journal_code": journal.code,
                            "date": fields.Date.today(),
                        },
                    }
                )
                statement.journal_id = journal.id
                self.statement_id = statement.id
            self.move_line_ids.create_statement_line_from_move_line(self.statement_id)
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.bank.statement",
                "view_mode": "form",
                "res_id": self.statement_id.id,
                "target": "current",
            }
        return True
