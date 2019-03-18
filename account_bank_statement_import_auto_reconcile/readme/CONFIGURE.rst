To configure this module, you need to:

#. go to the journal your bank account uses
#. in tab ``Automatic reconciliation rules``, add at least one rule

Reconciliation rules
~~~~~~~~~~~~~~~~~~~~

    Odoo standard
        Do exactly what Odoo does when proposing reconciliations. This searches for an exact match on amount and reference first, but falls back to less exact matches if none are found before. If there's only one match, do the reconciliation
    Exact amount and reference
        Strictly only match if we have the same partner, amount and reference. Check at least one field one the statement and one field on the move lines to tell the rule which fields to match with each other.
