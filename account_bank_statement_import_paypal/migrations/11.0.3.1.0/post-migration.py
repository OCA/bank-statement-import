# © 2024 FactorLibre - Aritz Olea <aritz.olea@factorlibre.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.ref(
        "account_bank_statement_import_paypal.paypal_statement_map_en"
    ).ref_transaction_id_column = "Reference Txn ID"
    env.ref(
        "account_bank_statement_import_paypal.paypal_activity_map_en"
    ).ref_transaction_id_column = "Reference Txn ID"
    env.ref(
        "account_bank_statement_import_paypal.paypal_statement_map_es"
    ).ref_transaction_id_column = "Id. de referencia de trans."
    env.ref(
        "account_bank_statement_import_paypal.paypal_activity_map_es"
    ).ref_transaction_id_column = "Id. de referencia de trans."
    env.ref(
        "account_bank_statement_import_paypal.paypal_statement_map_de"
    ).ref_transaction_id_column = "Ref Transaktionscode"
    env.ref(
        "account_bank_statement_import_paypal.paypal_activity_map_de"
    ).ref_transaction_id_column = "Ref Transaktionscode"
