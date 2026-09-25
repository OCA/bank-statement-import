# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

OLD_STRIPE_LABEL = (
    "stripe {source.metadata.invoice_number} {source.object} "
    "{source.id} {source.payment_method_details.type}"
)
NEW_STRIPE_LABEL = (
    "stripe {source.metadata.invoice_number} {source.payment_intent} "
    "{source.object} {source.id} {source.payment_method_details.type}"
)


def migrate(cr, version):
    cr.execute(
        """
        UPDATE online_bank_statement_provider
        SET stripe_label = %s
        WHERE stripe_label = %s
        """,
        (NEW_STRIPE_LABEL, OLD_STRIPE_LABEL),
    )
