1.  Go to *Invoicing \> Configuration \> Online Bank Statement
    Providers*, open a provider and click *Check Statements*.
2.  Choose the period and click *Check*.

The *Issues* tab lists the transactions missing in Odoo, the lines that
the provider does not know any more, and the lines whose amount or date
differ. The *Day by Day* tab compares, for each day, the total of the
lines in Odoo with the total of the provider, and the ending balance of
the statement of the day with the balance declared by the provider (for
the providers that give it). The first day that does not match is shown
at the top.

*Import Missing Lines* pulls the period again: the lines already
imported are skipped, so only the missing ones are created.
