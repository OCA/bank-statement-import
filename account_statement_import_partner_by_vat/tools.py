# Copyright 2026 Akretion (https://www.akretion.com).
# @author Renato Lima <renato.lima@akretion.com.br>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import re

# A VAT can be written with or without its usual punctuation, so we grab any
# run of digits and separators and normalize it afterwards. The run must start
# and end with a digit, which keeps the punctuation of the label itself out.
VAT_RUN_RE = re.compile(r"\d[\d./-]*\d")

CNPJ_LENGTH = 14
CPF_LENGTH = 11


def normalize_vat(vat):
    """Reduce a VAT number to the digits it is made of."""
    return re.sub(r"\D", "", vat or "")


def extract_vat_candidates(text):
    """Yield the normalized VAT numbers found in ``text``.

    Only well-formed Brazilian CNPJ/CPF are returned: their check digits make
    a match reliable enough to assign the partner of a statement line without
    any human review. A number of another length, or one whose check digits
    don't add up, is dropped rather than guessed.
    """
    seen = set()
    for match in VAT_RUN_RE.finditer(text):
        candidate = normalize_vat(match.group())
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_valid_cnpj(candidate) or is_valid_cpf(candidate):
            yield candidate


def is_valid_cpf(vat):
    """Check the 2 verification digits of a normalized CPF."""
    if len(vat) != CPF_LENGTH or len(set(vat)) == 1:
        return False
    for size in (9, 10):
        weights = range(size + 1, 1, -1)
        if _check_digit(vat[:size], weights) != vat[size]:
            return False
    return True


def is_valid_cnpj(vat):
    """Check the 2 verification digits of a normalized CNPJ."""
    if len(vat) != CNPJ_LENGTH or len(set(vat)) == 1:
        return False
    for size in (12, 13):
        # Weights cycle over 2..9, right to left: 5432987654 32 then 65432987654 32
        weights = [((size - 1 - i) % 8) + 2 for i in range(size)]
        if _check_digit(vat[:size], weights) != vat[size]:
            return False
    return True


def _check_digit(digits, weights):
    remainder = sum(int(d) * w for d, w in zip(digits, weights, strict=False)) % 11
    return "0" if remainder < 2 else str(11 - remainder)
