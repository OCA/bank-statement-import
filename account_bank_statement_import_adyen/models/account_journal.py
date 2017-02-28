# coding: utf-8
from openerp import fields, models


class Journal(models.Model):
    _inherit = 'account.journal'

    adyen_merchant_account = fields.Char(
        help=('Fill in the exact merchant account string to select this '
              'journal when importing Adyen statements'))
