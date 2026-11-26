This module adds support for the import of bank statements in `OFX format <https://en.wikipedia.org/wiki/Open_Financial_Exchange>`_.

Bank Statements may be generated containing a subset of the OFX information (only those transaction lines that are required for the
creation of the Financial Accounting records).

Since v14, this module support multi-account OFX files i.e. several different bank accounts in the same OFX file.

Each OFX field is imported into its corresponding statement line field:

* **Label** (``payment_ref``): the payee name (OFX ``NAME``), falling back to ``MEMO`` then ``TRNTYPE`` when the payee is missing
* **Note** (``narration``): ``MEMO`` and ``CHECKNUM``
* **Transaction Type** (``transaction_type``): ``TRNTYPE`` (debit, credit, directdebit, ...)
* **Reference** (``ref``): ``CHECKNUM`` when present

so reconciliation models can match on the Label, Note and Transaction Type conditions independently.

Upgrade note
~~~~~~~~~~~~

Earlier versions concatenated ``NAME``, ``CHECKNUM`` and ``MEMO`` into the Label field and discarded ``TRNTYPE``. Statement lines imported before the upgrade are not modified. For lines imported after it:

* reconciliation models whose **Label** conditions match on memo or check number content must move those conditions to **Note** or **Transaction Type**, otherwise they will stop matching
* reconciliation models with a **Transaction Type** condition could never match OFX-imported lines before (the field was empty) and may now start matching them
