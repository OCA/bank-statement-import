There is nothing to configure: set the VAT number on your partners and
import your statement files as usual.

A line is matched when its label contains a VAT number that is:

1.  syntactically valid, and
2.  set on exactly one commercial partner of the company of the journal.

The number may be written with or without its punctuation, so both
`PIX RECEBIDO 12.345.678/0001-95` and `TED 12345678000195 ACME` are
matched. Lines whose label repeats the VAT of the company itself, such as
bank fees or transfers between own accounts, are left untouched.

The default extractor only accepts Brazilian CNPJ and CPF, because their
check digits make a match reliable enough to assign a partner with no
human review. A number of any other length, or one whose check digits do
not add up, is ignored rather than guessed.

To support another country's numbering scheme, override
`extract_vat_candidates()` in `tools.py`. To scan other values of the line
than `partner_name`, `payment_ref`, `ref` and `narration`, override
`account.journal._statement_line_import_vat_match_fields()`.
